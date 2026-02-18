"""
API Provider Strategies for Model Registry

Contains strategies for OpenAI, Google, Anthropic, xAI, and DeepSeek.
"""

import json
import base64
import logging
import aiohttp
import asyncio
from typing import Dict, List, Optional, Any, AsyncGenerator
from app.security.encryption import decrypt_key
from app.chat.events import ModelEvent
from google import genai
from google.genai import types

from .base_provider import BaseProviderStrategy
from app.core.error_handlers import (
    ProviderError,
    APIKeyError,
    ModelNotFoundError,
    RateLimitError,
    ServiceUnavailableError
)

logger = logging.getLogger(__name__)

class OpenAIStrategy(BaseProviderStrategy):
    """Strategy for OpenAI provider using REST API"""
    
    def __init__(self):
        super().__init__(
            frontend_name="openai",
            backend_name="openai",
            api_base="https://api.openai.com/v1"
        )
    
    async def fetch_models(self, api_key: Optional[str] = None, session: Optional[aiohttp.ClientSession] = None) -> List[Dict[str, Any]]:
        if not api_key or not session: 
            return []
        
        try:
            self._log_request("fetch_models", "fetch_models")
            
            # Use standardized API key decryption
            decrypted_key = self._decrypt_api_key(api_key)

            async with session.get(
                f"{self._api_base}/models",
                headers={
                    "Authorization": f"Bearer {decrypted_key}",
                    "User-Agent": "LM-WebUI/1.0",
                    "Accept": "application/json"
                },
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    models = []
                    for model in data.get("data", []):
                        m_id = model.get("id", "").lower()
                        
                        # Basic validation to ensure it's a model object
                        if not model.get("id"):
                            continue
                        
                        is_vision = "vision" in m_id or "gpt-4o" in m_id or "gemini" in m_id or "claude-3" in m_id
                        is_image = "dall-e" in m_id or "image" in m_id
                        
                        # Determine context window roughly based on model name if not provided
                        context_window = 128000
                        if "gpt-4" in m_id: context_window = 128000
                        elif "128k" in m_id: context_window = 128000
                        elif "32k" in m_id: context_window = 32000
                        elif "16k" in m_id: context_window = 16384
                        elif "deepseek" in m_id: context_window = 64000
                        
                        models.append({
                            "id": model.get("id"),
                            "name": model.get("id"),
                            "provider": self._backend_name,
                            "context_window": context_window,
                            "supports_vision": is_vision,
                            "type": "image" if is_image else "chat"
                        })
                    
                    self._log_response("fetch_models", "fetch_models", True, model_count=len(models))
                    return models
                
                # Handle API error with standardized error handling
                error_text = await resp.text()
                self._handle_api_error(resp.status, error_text, self._backend_name)
                return []
                
        except Exception as e:
            logger.error(f"Error fetching models for {self._backend_name}: {e}")
            self._log_response("fetch_models", "fetch_models", False, error=str(e))
            return []

    async def generate(self, model: str, messages: List[Dict[str, str]], api_key: str, session: aiohttp.ClientSession, **kwargs) -> str:
        self._log_request(model, "generate", message_count=len(messages))
        
        # Use standardized API key decryption
        decrypted_key = self._decrypt_api_key(api_key)

        payload = {
            "model": model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 4000),
            "stream": False
        }
        
        async with session.post(
            f"{self._api_base}/chat/completions",
            headers={"Authorization": f"Bearer {decrypted_key}", "Content-Type": "application/json"},
            json=payload
        ) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                self._handle_api_error(resp.status, error_text, self._backend_name)
            
            data = await resp.json()
            response_text = data["choices"][0]["message"]["content"]
            
            self._log_response(model, "generate", True, response_length=len(response_text))
            return response_text

    async def stream(self, model: str, messages: List[Dict[str, str]], api_key: str, session: aiohttp.ClientSession, **kwargs) -> AsyncGenerator[str, None]:
        self._log_request(model, "stream", message_count=len(messages))
        
        # Use standardized API key decryption
        decrypted_key = self._decrypt_api_key(api_key)

        payload = {
            "model": model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 4000),
            "stream": True
        }
        
        async with session.post(
            f"{self._api_base}/chat/completions",
            headers={"Authorization": f"Bearer {decrypted_key}", "Content-Type": "application/json"},
            json=payload
        ) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                self._handle_api_error(resp.status, error_text, self._backend_name)
            
            async for line in resp.content:
                line = line.decode('utf-8').strip()
                if line.startswith('data: ') and line != 'data: [DONE]':
                    try:
                        data = json.loads(line[6:])
                        content = data["choices"][0]["delta"].get("content", "")
                        if content:
                            yield content
                    except json.JSONDecodeError:
                        continue
            
            self._log_response(model, "stream", True)

    async def stream_chat(self, model: str, messages: List[Dict[str, str]], api_key: str, session: aiohttp.ClientSession, **kwargs) -> AsyncGenerator[ModelEvent, None]:
        """Stream chat with ModelEvent objects for unified streaming"""
        # Use the common implementation pattern from base class
        async for event in self._stream_with_events(model, messages, api_key, session, **kwargs):
            yield event

    async def generate_image(self, model: str, prompt: str, api_key: str, session: aiohttp.ClientSession, **kwargs) -> Dict[str, Any]:
        self._log_request(model, "generate_image", prompt_length=len(prompt))
        
        # Use standardized API key decryption
        decrypted_key = self._decrypt_api_key(api_key)
            
        payload = {
            "model": model,
            "prompt": prompt,
            "n": 1,
            "size": kwargs.get("size", "1024x1024"),
            "response_format": "b64_json" 
        }
        
        async with session.post(
            f"{self._api_base}/images/generations",
            headers={"Authorization": f"Bearer {decrypted_key}", "Content-Type": "application/json"},
            json=payload
        ) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                self._handle_api_error(resp.status, error_text, self._backend_name)
            
            data = await resp.json()
            b64_data = data["data"][0]["b64_json"]
            image_data = base64.b64decode(b64_data)
            
            self._log_response(model, "generate_image", True, image_size=len(image_data))
            return {"data": image_data, "mime_type": "image/png"}


class GoogleStrategy(BaseProviderStrategy):
    """Strategy for Google/Gemini provider using google-genai SDK (v1.0+)"""
    
    def __init__(self):
        super().__init__(
            frontend_name="google",
            backend_name="google"
        )
    
    async def fetch_models(self, api_key: Optional[str] = None, session: Optional[aiohttp.ClientSession] = None) -> List[Dict[str, Any]]:
        if not api_key: 
            return []
        
        try:
            self._log_request("fetch_models", "fetch_models")
            
            # Use standardized API key decryption
            decrypted_key = self._decrypt_api_key(api_key)
            
            # Sanitize key (remove whitespace/newlines)
            if decrypted_key:
                decrypted_key = decrypted_key.strip()
                
            client = genai.Client(api_key=decrypted_key)
            
            models = []
            # Get pager from async list method - returns an AsyncPager
            # Use config to get base models (query_base=True) with reasonable page size
            pager = await client.aio.models.list(config={'page_size': 50, 'query_base': True})
            
            # Iterate through pager items (AsyncPager is an async iterator)
            async for m in pager:
                try:
                    # Check supported actions in new SDK structure (v1.62.0+)
                    # SDK uses supported_actions list of strings, not supported_generation_methods
                    actions = getattr(m, "supported_actions", [])
                    
                    if "generateContent" in actions:
                        name = m.name.lower()
                        # Clean ID: models/gemini-pro -> gemini-pro
                        raw_id = m.name.split('/')[-1] if '/' in m.name else m.name
                        model_id = raw_id.lower().replace(" ", "-")
                        
                        models.append({
                            "id": model_id,
                            "name": m.display_name or model_id,
                            "provider": self._backend_name,
                            "context_window": getattr(m, "input_token_limit", 128000),
                            "supports_vision": "vision" in name or "gemini-3" in name or "gemini-2.5" in name
                        })
                except Exception as model_err:
                    logger.warning(f"Error processing Google model {getattr(m, 'name', 'unknown')}: {model_err}")
                    continue
            
            self._log_response("fetch_models", "fetch_models", True, model_count=len(models))
            return models
        except Exception as e:
            logger.error(f"Error fetching Google models via SDK: {e}")
            self._log_response("fetch_models", "fetch_models", False, error=str(e))
            import traceback
            logger.error(traceback.format_exc())
            return []

    def _format_model_name(self, model_id: str) -> str:
        """Ensure model ID is correctly prefixed for Google SDK (models/ prefix)"""
        # Clean up model ID: lowercase and replace spaces with hyphens
        clean_id = model_id.lower().replace(" ", "-")
        
        # Map aliases
        if clean_id == "nano-banana":
            clean_id = "gemini-2.5-flash-image"
        elif clean_id == "nano-banana-pro":
            clean_id = "gemini-3-pro-image-preview"
            
        if not clean_id.startswith("models/"):
            return f"models/{clean_id}"
        return clean_id

    def _convert_messages(self, messages: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        contents = []
        for msg in messages:
            role = "model" if msg["role"] == "assistant" else "user"
            if msg["role"] == "system":
                role = "user"
                contents.append({"role": role, "parts": [{"text": "System Instruction: " + msg["content"]}]})
            else:
                contents.append({"role": role, "parts": [{"text": msg["content"]}]})
        return contents

    async def generate(self, model: str, messages: List[Dict[str, str]], api_key: str, session: aiohttp.ClientSession, **kwargs) -> str:
        model_name = self._format_model_name(model)
        self._log_request(model, "generate", message_count=len(messages))
        
        # Use standardized API key decryption
        decrypted_key = self._decrypt_api_key(api_key)

        if decrypted_key:
            decrypted_key = decrypted_key.strip()

        client = genai.Client(api_key=decrypted_key)
        
        contents = self._convert_messages(messages)
        
        config = types.GenerateContentConfig(
            temperature=kwargs.get("temperature", 0.7),
            max_output_tokens=kwargs.get("max_tokens", 4000)
        )
        
        try:
            response = await client.aio.models.generate_content(
                model=model_name,
                contents=contents,
                config=config
            )
            response_text = response.text
            
            self._log_response(model, "generate", True, response_length=len(response_text))
            return response_text
        except Exception as e:
            logger.error(f"Google SDK Generate Error: {e}")
            self._log_response(model, "generate", False, error=str(e))
            raise ProviderError(
                provider=self._backend_name,
                message=f"Google SDK generation error: {str(e)}",
                details={"model": model, "error_type": e.__class__.__name__}
            )

    async def stream(self, model: str, messages: List[Dict[str, str]], api_key: str, session: aiohttp.ClientSession, **kwargs) -> AsyncGenerator[str, None]:
        model_name = self._format_model_name(model)
        self._log_request(model, "stream", message_count=len(messages))
        
        # Use standardized API key decryption
        decrypted_key = self._decrypt_api_key(api_key)

        if decrypted_key:
            decrypted_key = decrypted_key.strip()

        client = genai.Client(api_key=decrypted_key)
        
        contents = self._convert_messages(messages)
        
        config = types.GenerateContentConfig(
            temperature=kwargs.get("temperature", 0.7),
            max_output_tokens=kwargs.get("max_tokens", 4000)
        )
        
        try:
            async for chunk in await client.aio.models.generate_content_stream(
                model=model_name,
                contents=contents,
                config=config
            ):
                if chunk.text:
                    yield chunk.text
            
            self._log_response(model, "stream", True)
        except Exception as e:
            logger.error(f"Google SDK Stream Error: {e}")
            self._log_response(model, "stream", False, error=str(e))
            raise ProviderError(
                provider=self._backend_name,
                message=f"Google SDK streaming error: {str(e)}",
                details={"model": model, "error_type": e.__class__.__name__}
            )

    async def stream_chat(self, model: str, messages: List[Dict[str, str]], api_key: str, session: aiohttp.ClientSession, **kwargs) -> AsyncGenerator[ModelEvent, None]:
        """Stream chat with ModelEvent objects for unified streaming"""
        # Use the common implementation pattern from base class
        async for event in self._stream_with_events(model, messages, api_key, session, **kwargs):
            yield event

    async def generate_image(self, model: str, prompt: str, api_key: str, session: aiohttp.ClientSession, **kwargs) -> Dict[str, Any]:
        model_name = self._format_model_name(model)
        self._log_request(model, "generate_image", prompt_length=len(prompt))
        
        # Use standardized API key decryption
        decrypted_key = self._decrypt_api_key(api_key)

        if decrypted_key:
            decrypted_key = decrypted_key.strip()

        client = genai.Client(api_key=decrypted_key)
        
        try:
            # Configure specifically for image generation
            # Gemini image models require explicitly requesting IMAGE modality
            config = types.GenerateContentConfig(
                response_modalities=["IMAGE"]
            )

            # Use SDK for image generation (Nano Banana support)
            response = await client.aio.models.generate_content(
                model=model_name,
                contents=[prompt],
                config=config
            )
            
            # Extract image from response parts
            if hasattr(response, 'parts'):
                for part in response.parts:
                    # Check for inline data (standard response)
                    if hasattr(part, 'inline_data') and part.inline_data:
                        image_data = part.inline_data.data
                        # Ensure we have bytes
                        if isinstance(image_data, str):
                            try:
                                # Try decoding if it's base64 string (some SDK versions)
                                image_data = base64.b64decode(image_data)
                            except:
                                # If prompt for bytes, encode it
                                image_data = image_data.encode('utf-8')
                                
                        result = {
                            "data": image_data, 
                            "mime_type": part.inline_data.mime_type
                        }
                        
                        self._log_response(model, "generate_image", True, image_size=len(image_data))
                        return result
            
            # Additional check for 'bytes' attribute if inline_data is not directly available
            # or if the structure is slightly different in newer SDK versions
            if hasattr(response, 'parts'):
                 for part in response.parts:
                     if hasattr(part, 'image') and part.image:
                         # Some versions might expose .image
                         result = {
                             "data": part.image.data,
                             "mime_type": "image/png"
                         }
                         
                         self._log_response(model, "generate_image", True, image_size=len(part.image.data))
                         return result

            error_msg = f"No image data found in SDK response. Parts: {len(response.parts) if hasattr(response, 'parts') else 0}"
            self._log_response(model, "generate_image", False, error=error_msg)
            raise ProviderError(
                provider=self._backend_name,
                message=error_msg,
                details={"model": model, "response_parts": len(response.parts) if hasattr(response, 'parts') else 0}
            )
            
        except Exception as e:
            logger.error(f"Google SDK Image Generation Error: {e}")
            self._log_response(model, "generate_image", False, error=str(e))
            raise ProviderError(
                provider=self._backend_name,
                message=f"Google SDK image generation error: {str(e)}",
                details={"model": model, "error_type": e.__class__.__name__}
            )

class AnthropicStrategy(BaseProviderStrategy):
    """Strategy for Anthropic/Claude provider"""
    
    def __init__(self):
        super().__init__(
            frontend_name="anthropic",
            backend_name="anthropic",
            api_base="https://api.anthropic.com/v1"
        )
    
    async def fetch_models(self, api_key: Optional[str] = None, session: Optional[aiohttp.ClientSession] = None) -> List[Dict[str, Any]]:
        if not api_key or not session: 
            return []
        
        try:
            self._log_request("fetch_models", "fetch_models")
            
            # Use standardized API key decryption
            decrypted_key = self._decrypt_api_key(api_key)

            async with session.get(
                f"{self._api_base}/models",
                headers={
                    "x-api-key": decrypted_key,
                    "anthropic-version": "2023-06-01"
                },
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    models = []
                    for model in data.get("data", []):
                        m_id = model.get("id", "").lower()
                        # Skip older models if desired, but for now list all compatible
                        if "claude" in m_id:
                            models.append({
                                "id": model.get("id"),
                                "name": model.get("display_name", model.get("id")),
                                "provider": self._backend_name,
                                "context_window": 200000, # Most Claude 3 models are 200k
                                "supports_vision": "claude-3" in m_id,
                                "type": "chat"
                            })
                    
                    self._log_response("fetch_models", "fetch_models", True, model_count=len(models))
                    return models
                
                # Handle API error with standardized error handling
                error_text = await resp.text()
                self._handle_api_error(resp.status, error_text, self._backend_name)
                return []
                
        except Exception as e:
            logger.error(f"Error fetching Anthropic models: {e}")
            self._log_response("fetch_models", "fetch_models", False, error=str(e))
            return []

    def _convert_messages(self, messages: List[Dict[str, str]]) -> tuple[Optional[str], List[Dict[str, str]]]:
        system_prompt = None
        anthropic_msgs = []
        for msg in messages:
            if msg["role"] == "system":
                system_prompt = msg["content"]
            else:
                anthropic_msgs.append({"role": msg["role"], "content": msg["content"]})
        return system_prompt, anthropic_msgs

    async def generate(self, model: str, messages: List[Dict[str, str]], api_key: str, session: aiohttp.ClientSession, **kwargs) -> str:
        self._log_request(model, "generate", message_count=len(messages))
        
        # Use standardized API key decryption
        decrypted_key = self._decrypt_api_key(api_key)
        system, msgs = self._convert_messages(messages)
        
        payload = {
            "model": model,
            "messages": msgs,
            "max_tokens": kwargs.get("max_tokens", 4000),
            "temperature": kwargs.get("temperature", 0.7)
        }
        if system:
            payload["system"] = system

        async with session.post(
            f"{self._api_base}/messages",
            headers={
                "x-api-key": decrypted_key, 
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json"
            },
            json=payload
        ) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                self._handle_api_error(resp.status, error_text, self._backend_name)
            
            data = await resp.json()
            response_text = data["content"][0]["text"]
            
            self._log_response(model, "generate", True, response_length=len(response_text))
            return response_text

    async def stream(self, model: str, messages: List[Dict[str, str]], api_key: str, session: aiohttp.ClientSession, **kwargs) -> AsyncGenerator[str, None]:
        self._log_request(model, "stream", message_count=len(messages))
        
        # Use standardized API key decryption
        decrypted_key = self._decrypt_api_key(api_key)
        system, msgs = self._convert_messages(messages)
        
        payload = {
            "model": model,
            "messages": msgs,
            "max_tokens": kwargs.get("max_tokens", 4000),
            "temperature": kwargs.get("temperature", 0.7),
            "stream": True
        }
        if system:
            payload["system"] = system

        async with session.post(
            f"{self._api_base}/messages",
            headers={
                "x-api-key": decrypted_key, 
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json"
            },
            json=payload
        ) as resp:
            if resp.status != 200:
                error_text = await resp.text()
                self._handle_api_error(resp.status, error_text, self._backend_name)
            
            async for line in resp.content:
                line = line.decode('utf-8').strip()
                if line.startswith('data: '):
                    try:
                        data = json.loads(line[6:])
                        if data["type"] == "content_block_delta" and data["delta"]["type"] == "text_delta":
                            yield data["delta"]["text"]
                    except json.JSONDecodeError:
                        continue
            
            self._log_response(model, "stream", True)

    async def stream_chat(self, model: str, messages: List[Dict[str, str]], api_key: str, session: aiohttp.ClientSession, **kwargs) -> AsyncGenerator[ModelEvent, None]:
        """Stream chat with ModelEvent objects for unified streaming"""
        # Use the common implementation pattern from base class
        async for event in self._stream_with_events(model, messages, api_key, session, **kwargs):
            yield event


class XAIStrategy(OpenAIStrategy):
    """Strategy for xAI/Grok provider (OpenAI Compatible)"""
    def __init__(self):
        super().__init__()
        self._frontend_name = "xai"
        self._backend_name = "xai"
        self._api_base = "https://api.x.ai/v1"


class DeepSeekStrategy(OpenAIStrategy):
    """Strategy for DeepSeek provider (OpenAI Compatible)"""
    def __init__(self):
        super().__init__()
        self._frontend_name = "deepseek"
        self._backend_name = "deepseek"
        self._api_base = "https://api.deepseek.com"


class ZhipuStrategy(OpenAIStrategy):
    """Strategy for Zhipu AI (GLM) provider (OpenAI Compatible)"""
    def __init__(self):
        super().__init__()
        self._frontend_name = "zhipu"
        self._backend_name = "zhipu"
        self._api_base = "https://open.bigmodel.cn/api/paas/v4"

    async def fetch_models(self, api_key: Optional[str] = None, session: Optional[aiohttp.ClientSession] = None) -> List[Dict[str, Any]]:
        models = []
        
        try:
            # Try to fetch from API
            models = await super().fetch_models(api_key, session)
            # Post-process for Zhipu specific features
            for model in models:
                m_id = model["id"].lower()
                if "glm-4.6v" in m_id or "vision" in m_id:
                    model["supports_vision"] = True
                if "glm-4.7-flash" in m_id:
                    model["context_window"] = 128000
        except Exception as e:
            logger.warning(f"Failed to fetch Zhipu models from API: {e}")
            # Return fallback models when API fails
            models = self._get_fallback_models("zhipu")
        
        return models





