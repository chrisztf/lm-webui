"""
Streaming Service Layer

Handles LLM response generation and streaming with clean separation from WebSocket protocol.
Supports both regular streaming and reasoning-enhanced streaming.
"""
import asyncio
import json
from datetime import datetime
from typing import Dict, Any, Optional, AsyncGenerator
from app.services.model_registry import get_model_registry
from app.streaming.session import streaming_manager, create_streaming_session, cancel_streaming_session
from app.streaming.event_system import StreamingEvent, EventType
from app.streaming.events import create_cancelled_event, create_error_event, create_session_start_event
from app.rag.web_search import web_engine


class StreamingService:
    """Service for handling LLM response streaming"""
    
    def __init__(self):
        self.model_registry = get_model_registry()
    
    async def start_streaming(
        self,
        message: str,
        provider: str,
        model: str,
        user_id: int,
        conversation_history: Optional[list] = None,
        deep_thinking: bool = False,
        web_search: bool = False,
        search_provider: str = "duckduckgo",
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Start a streaming session
        
        Returns: Initial session information
        """
        # Validate parameters
        validation_result = self._validate_streaming_params(
            message, provider, model, conversation_history
        )
        if not validation_result["valid"]:
            raise ValueError(validation_result["error"])
        
        # Create or use existing session
        session_id = session_id or create_streaming_session()
        
        # Get API key for the provider
        api_key = await self._get_api_key_for_provider(provider, user_id)
        if not api_key and provider not in ["ollama", "lmstudio", "gguf"]:
            raise ValueError(f"API key required for {provider} provider")
            
        # Perform Web Search if enabled
        search_context = ""
        if web_search:
            try:
                # Note: Ideally we should yield status updates here, but since this is called
                # before the generator starts, we can't easily yield events to the websocket
                # unless we refactor to pass the websocket or a callback.
                # For now, we proceed with the search and inject the context.
                
                scrape_result = await web_engine.search_and_scrape(
                    query=message, 
                    max_results=3,
                    scrape_length=2500,
                    provider=search_provider,
                    user_id=user_id
                )
                search_results = scrape_result.get("results", [])
                
                if search_results:
                    current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                    search_context = f"CRITICAL: REAL-TIME WEB SEARCH RESULTS ({current_time_str}):\n"
                    search_context += "Use these results to answer the query. If they conflict with training data, prioritize these results.\n\n"
                    
                    for i, result in enumerate(search_results):
                        search_context += f"Source [{i+1}]: {result.get('title', 'No Title')}\n"
                        search_context += f"URL: {result.get('url', '')}\n"
                        content = result.get('scraped_content', '')
                        if content:
                            content = content[:2000]
                            search_context += f"Content: {content}\n"
                        else:
                             search_context += f"Snippet: {result.get('description', '') or result.get('body', 'No description available.')}\n"
                        search_context += "\n---\n"
            except Exception as e:
                print(f"Web search failed in streaming service: {e}")
        
        # Create enhanced prompt with context
        prompt = self._create_prompt(message, conversation_history, deep_thinking, search_context)
        
        return {
            "session_id": session_id,
            "prompt": prompt,
            "provider": provider,
            "model": model,
            "api_key": api_key,
            "deep_thinking": deep_thinking,
            "user_id": user_id
        }
    
    async def stream_response(
        self,
        session_id: str,
        prompt: str,
        provider: str,
        model: str,
        api_key: str,
        deep_thinking: bool = False
    ) -> AsyncGenerator[str, None]:
        """
        Stream LLM response
        
        Yields: Response chunks
        """
        try:
            # Get strategy from model registry
            strategy = self.model_registry.get_strategy(provider)
            if not strategy:
                raise ValueError(f"Unsupported provider: {provider}")
            
            # Get session
            session = await self.model_registry.get_session()
            
            # Prepare messages
            messages = [
                {"role": "user", "content": prompt}
            ]
            
            # Stream response
            async for chunk in strategy.stream(
                model=model,
                messages=messages,
                api_key=api_key,
                session=session,
                max_tokens=4000,
                temperature=0.7
            ):
                yield chunk
                
        except Exception as e:
            error_event = create_error_event(f"Streaming error: {str(e)}", session_id)
            streaming_manager.emit_event(error_event)
            raise
    
    async def stop_streaming(self, session_id: str) -> Dict[str, Any]:
        """Stop a streaming session"""
        # Cancel the session tasks
        cancel_streaming_session(session_id)
        
        # Explicitly remove from manager to ensure no zombie state
        # We use the manager instance directly as cleanup_session might not be exported as helper
        streaming_manager.cleanup_session(session_id)
        
        return {
            "session_id": session_id,
            "status": "cancelled",
            "message": "Streaming session cancelled"
        }
    
    def _validate_streaming_params(
        self,
        message: str,
        provider: str,
        model: str,
        conversation_history: Optional[list]
    ) -> Dict[str, Any]:
        """Validate streaming parameters"""
        # Validate message
        message = message.strip()
        if not message:
            return {"valid": False, "error": "Message is required"}
        if len(message) > 10000:
            return {"valid": False, "error": "Message too long (max 10000 characters)"}
        
        # Validate provider
        provider = provider.lower()
        valid_providers = ["openai", "claude", "gemini", "grok", "deepseek", "lmstudio", "ollama", "gguf"]
        
        # Also allow dynamic providers from registry if possible, but keep list for safety
        if provider not in valid_providers:
             # Fallback check against registry just in case
            try:
                registry = self.model_registry
                if hasattr(registry, "_strategies") and provider in registry._strategies:
                    pass # Valid
                else:
                    return {"valid": False, "error": f"Invalid provider. Supported: {', '.join(valid_providers)}"}
            except:
                return {"valid": False, "error": f"Invalid provider. Supported: {', '.join(valid_providers)}"}
        
        # Validate model
        if not model or len(model) < 2:
            return {"valid": False, "error": "Valid model name is required"}
        
        # Validate conversation history
        if conversation_history and not isinstance(conversation_history, list):
            return {"valid": False, "error": "Conversation history must be an array"}
        
        return {"valid": True, "error": None}
    
    async def _get_api_key_for_provider(self, provider: str, user_id: int) -> Optional[str]:
        """Get API key for provider from user's stored keys"""
        try:
            user_keys = self.model_registry.get_user_api_keys(user_id)
            api_key = user_keys.get(provider)
            if not api_key:
                strategy = self.model_registry.get_strategy(provider)
                if strategy:
                    api_key = user_keys.get(strategy.get_backend_name())
            return api_key
        except Exception:
            return None
    
    def _create_prompt(
        self,
        message: str,
        conversation_history: Optional[list] = None,
        deep_thinking: bool = False,
        search_context: str = ""
    ) -> str:
        """Create prompt for LLM"""
        
        # Inject search context if present
        full_message = message
        if search_context:
            full_message = f"{search_context}\n\nUser Query: {message}"
            
        if deep_thinking:
            return f"""Analyze this query with step-by-step reasoning: {full_message}
You MUST perform step-by-step reasoning before answering.
You MUST wrap your entire thought process in <think> and </think> tags at the very beginning of your response.
Do NOT output anything before the <think> tag.
Inside the <think> block, you should:
1. Break down the user's query.
2. Inject search result if available, if not skip.
3. Consider multiple approaches.
4. Verify your facts and logic.
5. Formulate the final answer.

CRITICAL: Your response must start exactly with <think> followed by your reasoning, then </think>, then your final answer.

Example:
<think>
[Step-by-step reasoning process here...]
</think>
[Your final answer here]

Your final response should follow the thinking block
"""
        else:
            # If magic wand was used, the instruction is already in the message (plain text)
            # We assume no manual BOS tokens (like <|user|>) are present, relying on the model's chat template
            return full_message


# Global streaming service instance
_streaming_service = None

def get_streaming_service() -> StreamingService:
    """Get global streaming service instance"""
    global _streaming_service
    if _streaming_service is None:
        _streaming_service = StreamingService()
    return _streaming_service
