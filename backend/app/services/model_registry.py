"""
Unified Model Registry with Strategy Pattern

This module provides a centralized ModelRegistry that uses strategy pattern
for different provider types. Concrete strategies are now separated into:
- model_provider.py (API-based providers)
- model_local.py (Local hosting providers)
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, AsyncGenerator, Union
import asyncio
import aiohttp
import logging

from app.security.encryption import decrypt_key
from app.database import get_db
from app.services.performance_monitor import get_performance_monitor

# Import concrete strategies
from .model_provider import (
    OpenAIStrategy, 
    GoogleStrategy, 
    AnthropicStrategy, 
    XAIStrategy, 
    DeepSeekStrategy,
    ZhipuStrategy
)
from .model_local import (
    LMStudioStrategy, 
    OllamaStrategy, 
    GGUFStrategy
)

logger = logging.getLogger(__name__)

# ============================================================================
# CONSTANTS: Consolidated Fallback Models
# ============================================================================

FALLBACK_MODELS = {
    "openai": [
        # GPT-5.2: The Feb 2026 flagship. Unified reasoning + multimodal.
        {"id": "gpt-5.2", "name": "GPT-5.2 (Flagship)", "provider": "openai", "context_window": 400000, "supports_vision": True},
        {"id": "gpt-5.1", "name": "GPT-5.1 (Stable)", "provider": "openai", "context_window": 200000, "supports_vision": True},
        {"id": "gpt-5-mini", "name": "GPT-5 Mini", "provider": "openai", "context_window": 128000, "supports_vision": True},
        {"id": "gpt-realtime-mini", "name": "GPT Realtime Mini", "provider": "openai", "context_window": 64000, "supports_vision": False},
        {"id": "gpt-5.1-codex-mini", "name": "GPT-5.1 Codex Mini", "provider": "openai", "context_window": 128000, "supports_vision": True},
    ],
    "google": [
        # Gemini 3.0 Pro leads 2026 with massive context and native multimodal
        {"id": "gemini-3-pro", "name": "Gemini 3.0 Pro", "provider": "google", "context_window": 1000000, "supports_vision": True},
        {"id": "gemini-3-flash", "name": "Gemini 3.0 Flash", "provider": "google", "context_window": 1000000, "supports_vision": True},
        {"id": "gemini-2.5-flash", "name": "Gemini 2.5 Flash", "provider": "google", "context_window": 1000000, "supports_vision": True},
    ],
    "anthropic": [
        # Claude 4.6 (Feb 2026) introduced the "Adaptive Thinking" and 1M window
        {"id": "claude-4-6-opus", "name": "Claude 4.6 Opus", "provider": "anthropic", "context_window": 1000000, "supports_vision": True},
        {"id": "claude-4-5-sonnet", "name": "Claude 4.5 Sonnet", "provider": "anthropic", "context_window": 200000, "supports_vision": True},
        {"id": "claude-4-5-haiku", "name": "Claude 4.5 Haiku", "provider": "anthropic", "context_window": 200000, "supports_vision": True},
    ],
    "xai": [
        # Grok 4.1 "Real-Time Rebel" series
        {"id": "grok-4-1-reasoning", "name": "Grok 4.1 Reasoning", "provider": "xai", "context_window": 1000000, "supports_vision": True},
        {"id": "grok-4-1-fast", "name": "Grok 4.1 Fast", "provider": "xai", "context_window": 2000000, "supports_vision": True},
    ],
    "deepseek": [
        # DeepSeek-V3.2 released late 2025/early 2026 as a "Reasoning-First" agent king
        {"id": "deepseek-v3.2", "name": "DeepSeek V3.2", "provider": "deepseek", "context_window": 128000, "supports_vision": False},
        {"id": "deepseek-v3.2-speciale", "name": "DeepSeek V3.2 Speciale", "provider": "deepseek", "context_window": 128000, "supports_vision": True},
        {"id": "deepseek-r2-pro", "name": "DeepSeek R2 Pro", "provider": "deepseek", "context_window": 128000, "supports_vision": False},
    ],
    "zhipu": [
        # Zhipu AI (Z.ai) GLM-4.7/4.6 series
        {"id": "glm-4.7-pro", "name": "GLM-4.7 Pro", "provider": "zhipu", "context_window": 128000, "supports_vision": True},
        {"id": "glm-4.7-flash", "name": "GLM-4.7 Flash", "provider": "zhipu", "context_window": 128000, "supports_vision": True},
        {"id": "glm-4.6v-flash", "name": "GLM-4.6 Vision Flash", "provider": "zhipu", "context_window": 128000, "supports_vision": True},
        {"id": "glm-4.6v", "name": "GLM-4.6 Vision", "provider": "zhipu", "context_window": 128000, "supports_vision": True},
    ]
}

# ============================================================================
# STRATEGY PATTERN: Provider Strategies (Base)
# ============================================================================

class ProviderStrategy(ABC):
    """Abstract base class for provider strategies"""
    
    @abstractmethod
    async def fetch_models(self, api_key: Optional[str] = None, session: Optional[aiohttp.ClientSession] = None) -> List[Dict[str, Any]]:
        """Fetch models from this provider"""
        pass
    
    @abstractmethod
    async def generate(self, model: str, messages: List[Dict[str, str]], api_key: str, session: aiohttp.ClientSession, **kwargs) -> str:
        """Generate response (non-streaming)"""
        pass

    @abstractmethod
    async def stream(self, model: str, messages: List[Dict[str, str]], api_key: str, session: aiohttp.ClientSession, **kwargs) -> AsyncGenerator[str, None]:
        """Stream response"""
        pass

    async def generate_image(self, model: str, prompt: str, api_key: str, session: aiohttp.ClientSession, **kwargs) -> Dict[str, Any]:
        """
        Generate image
        Returns: Dict with 'data' (bytes) or 'url' (str)
        """
        raise NotImplementedError(f"Image generation not supported by {self.get_provider_name()}")

    @abstractmethod
    def get_provider_name(self) -> str:
        """Get the provider name (frontend name)"""
        pass
    
    @abstractmethod
    def get_backend_name(self) -> str:
        """Get the backend provider name (API name)"""
        pass
    
    def _get_fallback_models(self, provider_key: str) -> List[Dict[str, Any]]:
        """Get fallback models from consolidated constant"""
        return FALLBACK_MODELS.get(provider_key, [])
        

# ============================================================================
# MODEL REGISTRY
# ============================================================================

class ModelRegistry:
    """
    Unified Model Registry that manages all model providers using strategy pattern.
    """
    
    def __init__(self):
        # Instantiate strategies
        openai = OpenAIStrategy()
        google = GoogleStrategy()
        anthropic = AnthropicStrategy()
        xai = XAIStrategy()
        deepseek = DeepSeekStrategy()
        zhipu = ZhipuStrategy()
        lmstudio = LMStudioStrategy()
        ollama = OllamaStrategy()
        gguf = GGUFStrategy()

        self._strategies: Dict[str, Any] = {
            "openai": openai,
            # Supporting both internal and frontend-facing provider names
            "google": google,
            "gemini": google,
            "anthropic": anthropic,
            "claude": anthropic,
            "xai": xai,
            "grok": xai,
            "deepseek": deepseek,
            "zhipu": zhipu,
            "lmstudio": lmstudio,
            "ollama": ollama,
            "gguf": gguf,
        }
        self._cache = {}
        self._session: Optional[aiohttp.ClientSession] = None
        self._performance_monitor = get_performance_monitor()
        self._provider_mapping = {
            'gemini': 'google', 'claude': 'anthropic', 'grok': 'xai', 'deepseek': 'deepseek',
            'google': 'google', 'anthropic': 'anthropic', 'xai': 'xai', 'zhipu': 'zhipu'
        }
    
    async def get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session
    
    async def close_session(self):
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
    
    def get_strategy(self, provider: str, user_id: Optional[int] = None) -> Optional[Any]:
        """Get strategy for provider, optionally with user-specific configuration"""
        strategy = self._strategies.get(provider)
        
        # For local providers, we need to check if user has configured a custom URL
        if provider in ["lmstudio", "ollama"] and user_id:
            api_keys = self.get_user_api_keys(user_id)
            url_key = f"{provider}_url"
            if url_key in api_keys:
                # Create a new strategy instance with the custom URL
                if provider == "lmstudio":
                    return LMStudioStrategy(base_url=api_keys[url_key])
                elif provider == "ollama":
                    return OllamaStrategy(base_url=api_keys[url_key])
        
        return strategy
    
    def get_user_api_keys(self, user_id: int) -> Dict[str, str]:
        db = get_db()
        try:
            keys = db.execute("SELECT provider, encrypted_key, base_url FROM api_keys WHERE user_id = ?", (user_id,)).fetchall()
            result = {}
            for p, k, url in keys:
                result[p] = k
                if p in self._provider_mapping:
                    result[self._provider_mapping[p]] = k
                if p in ["lmstudio", "ollama"] and url:
                    try:
                        decrypted_url = decrypt_key(url)
                        result[f"{p}_url"] = decrypted_url
                    except:
                        pass
            return result
        except Exception:
            keys = db.execute("SELECT provider, encrypted_key FROM api_keys WHERE user_id = ?", (user_id,)).fetchall()
            result = {}
            for p, k in keys:
                result[p] = k
                if p in self._provider_mapping:
                    result[self._provider_mapping[p]] = k
            return result
    
    async def fetch_models_for_user(self, user_id: int) -> List[Dict[str, Any]]:
        session = await self.get_session()
        api_keys = self.get_user_api_keys(user_id)
        
        tasks = []
        for provider, strategy in self._strategies.items():
            key = api_keys.get(provider) or api_keys.get(strategy.get_backend_name())
            tasks.append(strategy.fetch_models(key, session))
            
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_models = []
        for res in results:
            if isinstance(res, list): all_models.extend(res)
            
        return all_models

    async def fetch_models_for_provider(self, provider: str, user_id: int) -> List[Dict[str, Any]]:
        """Fetch models for a specific provider using user's API key"""
        strategy = self.get_strategy(provider, user_id)
        if not strategy:
            raise ValueError(f"Unsupported provider: {provider}")
        
        session = await self.get_session()
        api_keys = self.get_user_api_keys(user_id)
        
        key = api_keys.get(provider) or api_keys.get(strategy.get_backend_name())
        return await strategy.fetch_models(key, session)
    
    def get_kg_extraction_agent(self) -> str:
        """Ensure the 1B Knowledge Graph agent is ready and return its ID."""
        gguf_strategy = self.get_strategy("gguf")
        if hasattr(gguf_strategy, 'ensure_model'):
            filename = "Qwen3-1.7B-Q4_K_M.gguf"
            try:
                gguf_strategy.ensure_model(filename)
                return f"gguf:{filename}"
            except Exception as e:
                logger.error(f"Failed to prepare KG agent: {e}")
                return ""
        return ""

    async def get_model_context_window(self, model_id: str, user_id: int) -> int:
        """Get the context window for a specific model ID."""
        provider = "openai"
        if ":" in model_id:
            parts = model_id.split(":", 1)
            if parts[0] in self._strategies or parts[0] == "gguf":
                provider = parts[0]
        
        lower_id = model_id.lower()
        if "gpt-5" in lower_id: return 200000
        if "gpt-4" in lower_id: return 128000
        if "claude-4" in lower_id: return 200000
        if "claude-3" in lower_id: return 200000
        if "gemini-3" in lower_id: return 1000000
        if "gemini-2" in lower_id: return 1000000
        if "gemini-1.5" in lower_id: return 1000000
        if "llama-3" in lower_id: return 128000
        if "mistral" in lower_id: return 32000
        if "glm-4" in lower_id: return 128000
        if "deepseek" in lower_id: return 128000
        if "grok" in lower_id: return 1000000
        
        if provider == "gguf" or model_id.startswith("gguf:"):
             try:
                 models = await self.fetch_models_for_provider("gguf", user_id)
                 for m in models:
                     if m["id"] == model_id or m["name"] == model_id:
                         return m.get("context_window", 4096)
             except Exception:
                 pass
        
        return 4096

    def clear_cache(self, user_id: Optional[int] = None):
        self._cache.clear()

# Global ModelRegistry instance
_model_registry = None

def get_model_registry() -> ModelRegistry:
    global _model_registry
    if _model_registry is None:
        _model_registry = ModelRegistry()
    return _model_registry
