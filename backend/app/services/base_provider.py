"""
Base Provider Strategy with Standardized Patterns

This module provides a standardized base class for all provider strategies
with consistent error handling, logging, and API key management.
"""

import json
import logging
import aiohttp
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, AsyncGenerator

from app.security.encryption import decrypt_key
from app.chat.events import ModelEvent
from app.core.error_handlers import (
    ProviderError,
    APIKeyError,
    ModelNotFoundError,
    RateLimitError,
    ServiceUnavailableError
)

logger = logging.getLogger(__name__)


class BaseProviderStrategy(ABC):
    """Abstract base class for all provider strategies with standardized patterns"""
    
    def __init__(self, frontend_name: str, backend_name: str, api_base: Optional[str] = None):
        self._frontend_name = frontend_name
        self._backend_name = backend_name
        self._api_base = api_base or ""
        
    # ============================================================================
    # ABSTRACT METHODS (Must be implemented by subclasses)
    # ============================================================================
    
    @abstractmethod
    async def fetch_models(self, api_key: Optional[str] = None, 
                          session: Optional[aiohttp.ClientSession] = None) -> List[Dict[str, Any]]:
        """Fetch models from this provider"""
        pass
    
    @abstractmethod
    async def generate(self, model: str, messages: List[Dict[str, str]], 
                      api_key: str, session: aiohttp.ClientSession, **kwargs) -> str:
        """Generate response (non-streaming)"""
        pass
    
    @abstractmethod
    async def stream(self, model: str, messages: List[Dict[str, str]], 
                    api_key: str, session: aiohttp.ClientSession, **kwargs) -> AsyncGenerator[str, None]:
        """Stream response as raw text chunks"""
        pass
    
    @abstractmethod
    async def stream_chat(self, model: str, messages: List[Dict[str, str]], 
                         api_key: str, session: aiohttp.ClientSession, **kwargs) -> AsyncGenerator[ModelEvent, None]:
        """Stream response as ModelEvent objects for unified streaming"""
        pass
    
    # ============================================================================
    # STANDARDIZED UTILITY METHODS
    # ============================================================================
    
    def _decrypt_api_key(self, api_key: str) -> str:
        """
        Standardized API key decryption with consistent error handling.
        
        Args:
            api_key: Encrypted or plaintext API key
            
        Returns:
            Decrypted API key
            
        Raises:
            APIKeyError: If decryption fails and key appears to be encrypted
        """
        try:
            # Try to decrypt the key
            decrypted_key = decrypt_key(api_key)
            logger.debug(f"Successfully decrypted API key for {self._backend_name}")
            return decrypted_key
        except Exception as e:
            # If decryption fails, check if it might be plaintext
            # Simple heuristic: encrypted keys are usually longer and contain special chars
            if len(api_key) > 100 and '=' in api_key:
                # Looks like an encrypted key but decryption failed
                logger.error(f"Failed to decrypt API key for {self._backend_name}: {e}")
                raise APIKeyError(
                    provider=self._backend_name,
                    message="Failed to decrypt API key",
                    details={"error": str(e)}
                )
            else:
                # Probably plaintext, return as-is
                logger.debug(f"Using plaintext API key for {self._backend_name}")
                return api_key
    
    def _handle_api_error(self, status_code: int, error_text: str, provider: str) -> None:
        """
        Standardized API error handling with proper exception types.
        
        Args:
            status_code: HTTP status code
            error_text: Error response text
            provider: Provider name for logging
            
        Raises:
            Appropriate exception based on status code
        """
        logger.error(f"{provider} API error {status_code}: {error_text}")
        
        if status_code == 401:
            raise APIKeyError(
                provider=provider,
                message="Invalid API key or authentication failed",
                details={"status_code": status_code, "error": error_text}
            )
        elif status_code == 404:
            raise ModelNotFoundError(
                provider=provider,
                message="Model not found",
                details={"status_code": status_code, "error": error_text}
            )
        elif status_code == 429:
            raise RateLimitError(
                provider=provider,
                message="Rate limit exceeded",
                details={"status_code": status_code, "error": error_text}
            )
        elif status_code >= 500:
            raise ServiceUnavailableError(
                provider=provider,
                message="Service temporarily unavailable",
                details={"status_code": status_code, "error": error_text}
            )
        else:
            raise ProviderError(
                provider=provider,
                message=f"API error {status_code}",
                details={"status_code": status_code, "error": error_text}
            )
    
    def _log_request(self, model: str, operation: str, **kwargs) -> None:
        """
        Standardized request logging.
        
        Args:
            model: Model name/ID
            operation: Operation type (generate, stream, fetch_models, etc.)
            **kwargs: Additional context
        """
        log_context = {
            "provider": self._backend_name,
            "model": model,
            "operation": operation,
            **kwargs
        }
        logger.info(f"{self._backend_name} {operation} request", extra=log_context)
    
    def _log_response(self, model: str, operation: str, success: bool, **kwargs) -> None:
        """
        Standardized response logging.
        
        Args:
            model: Model name/ID
            operation: Operation type
            success: Whether the operation succeeded
            **kwargs: Additional context
        """
        log_context = {
            "provider": self._backend_name,
            "model": model,
            "operation": operation,
            "success": success,
            **kwargs
        }
        level = logger.info if success else logger.error
        level(f"{self._backend_name} {operation} response", extra=log_context)
    
    # ============================================================================
    # OPTIONAL METHODS (Can be overridden by subclasses)
    # ============================================================================
    
    async def generate_image(self, model: str, prompt: str, api_key: str, 
                            session: aiohttp.ClientSession, **kwargs) -> Dict[str, Any]:
        """
        Generate image (optional - not all providers support this)
        
        Returns:
            Dict with 'data' (bytes) or 'url' (str) and 'mime_type'
            
        Raises:
            NotImplementedError: If image generation is not supported
        """
        raise NotImplementedError(f"Image generation not supported by {self._backend_name}")
    
    def get_provider_name(self) -> str:
        """Get the provider name (frontend name)"""
        return self._frontend_name
    
    def get_backend_name(self) -> str:
        """Get the backend provider name (API name)"""
        return self._backend_name
    
    def get_api_base(self) -> str:
        """Get the API base URL"""
        return self._api_base
    
    def _get_fallback_models(self, provider_key: str) -> List[Dict[str, Any]]:
        """
        Get fallback models from consolidated constant.
        This should be imported from model_registry or defined here.
        """
        # Import here to avoid circular imports
        from .model_registry import FALLBACK_MODELS
        return FALLBACK_MODELS.get(provider_key, [])
    
    # ============================================================================
    # COMMON IMPLEMENTATION PATTERNS
    # ============================================================================
    
    async def _stream_with_events(self, model: str, messages: List[Dict[str, str]], 
                                 api_key: str, session: aiohttp.ClientSession, 
                                 **kwargs) -> AsyncGenerator[ModelEvent, None]:
        """
        Common pattern for streaming with ModelEvent objects.
        Subclasses can use this as a template.
        """
        try:
            # Send typing indicator
            yield ModelEvent.typing()
            
            self._log_request(model, "stream_chat", message_count=len(messages))
            
            # Decrypt API key
            decrypted_key = self._decrypt_api_key(api_key)
            
            # Call the actual stream implementation
            async for chunk in self.stream(model, messages, decrypted_key, session, **kwargs):
                if chunk:
                    yield ModelEvent.token(chunk)
            
            # Send completion event
            yield ModelEvent.done()
            self._log_response(model, "stream_chat", True)
            
        except Exception as e:
            error_msg = f"Stream error: {str(e)}"
            logger.error(f"{self._backend_name} stream_chat error: {e}")
            self._log_response(model, "stream_chat", False, error=str(e))
            yield ModelEvent.error(error_msg)