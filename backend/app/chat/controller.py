"""
Chat Controller - Orchestration Layer

Follows prompt32.md architecture:
- Transport ≠ Orchestration ≠ Provider ≠ RAGProcessor
- No cross-layer coupling
- Implements seamless chat pipeline with RAGProcessor integration
"""
import asyncio
import logging
from typing import AsyncGenerator, Optional, Dict, Any
from app.chat.events import ModelEvent
from app.chat.schemas import ChatRequest, RAGContextError, RAGResult, ChatValidationError
from app.chat.session_manager import get_chat_session_manager
from app.services.model_registry import get_model_registry
from app.rag.processor import RAGProcessor

logger = logging.getLogger(__name__)


class ChatController:
    """
    Orchestration layer that follows prompt32.md flow:
    
    1. Validate session
    2. Create job_id
    3. Emit typing event
    4. Call RAGProcessor
    5. Validate retrieval result
    6. Construct final prompt with anti-hallucination safeguards
    7. Select provider adapter
    8. Stream unified events
    9. Persist assistant response
    10. Emit done event
    """
    
    def __init__(self, rag_processor: Optional[RAGProcessor] = None):
        self.rag_processor = rag_processor
        self.model_registry = get_model_registry()
        self.session_manager = get_chat_session_manager()
        
        # Anti-hallucination safeguards
        self.context_guard_message = (
            "You must answer only using the provided context. "
            "If the information is not in the context, state that clearly. "
            "Do not make up information or use your training data."
        )
        self.max_context_tokens = 4000  # Conservative limit
    
    async def process_chat_request(
        self, 
        request: ChatRequest, 
        user_id: int,
        conversation_id: Optional[str] = None
    ) -> AsyncGenerator[ModelEvent, None]:
        """
        Process chat request following prompt32.md flow.
        
        Yields ModelEvent objects for WebSocket forwarding.
        """
        logger.info(f"Processing chat request: session={request.sessionId}, model={request.model}, provider={request.provider}, reasoning_mode={request.deepThinkingMode}, web_search={request.webSearch}")
        
        # 1. Validate session and prevent parallel streaming
        if not self.session_manager.can_start_streaming(request.sessionId):
            yield ModelEvent.error("Session already streaming")
            return
        
        # 2. Start streaming session
        if not self.session_manager.start_streaming(request.sessionId, request.job_id):
            yield ModelEvent.error("Failed to start streaming session")
            return
        
        # Initialize response accumulator
        response_content = ""
        
        try:
            # 3. Ensure conversation exists and save user message
            from app.chat.service import ensure_conversation_exists, save_message
            
            # Use conversation_id from request or generate from session
            actual_conversation_id = conversation_id or request.conversationId or request.sessionId
            
            # Ensure conversation exists
            try:
                actual_conversation_id = ensure_conversation_exists(actual_conversation_id, user_id)
            except ValueError as e:
                yield ModelEvent.error(str(e))
                return
            
            # Save user message
            metadata = {"attachments": request.file_references} if request.file_references else None
            save_message(
                actual_conversation_id, 
                user_id, 
                "user", 
                request.message, 
                metadata, 
                model=request.model, 
                provider=request.provider
            )
            
            # 4. Emit typing event
            yield ModelEvent.typing()
            
            # 5. Call RAGProcessor if required
            rag_result = None
            if request.requires_rag and self.rag_processor:
                try:
                    rag_result = await self._retrieve_rag_context(request)
                    
                    # 6. Validate retrieval result
                    if not rag_result.has_documents:
                        raise RAGContextError("No relevant documents found")
                    
                    logger.info(f"RAG retrieved {rag_result.source_count} documents")
                except RAGContextError as e:
                    yield ModelEvent.error(str(e))
                    return
                except Exception as e:
                    logger.error(f"RAG retrieval failed: {e}")
                    yield ModelEvent.error("Context retrieval failed")
                    return
            
            # 7. Construct final prompt with anti-hallucination safeguards
            prompt = self._construct_prompt(request.message, rag_result)
            
            # 8. Select provider adapter
            provider = self.model_registry.get_strategy(request.provider)
            if not provider:
                yield ModelEvent.error(f"Provider not available: {request.provider}")
                return
            
            # Get API key for the provider
            api_key = await self._get_api_key_for_provider(request.provider, request)
            if not api_key and request.provider not in ["ollama", "lmstudio", "gguf"]:
                yield ModelEvent.error(f"API key required for {request.provider}")
                return
            
            # 9. Stream with unified interface
            # Get session for HTTP requests
            session = await self.model_registry.get_session()
            
            # Prepare messages for provider
            messages = [{"role": "user", "content": prompt}]
            
            # Stream using the new stream_chat interface
            async for event in provider.stream_chat(
                model=request.model,
                messages=messages,
                api_key=api_key or "",
                session=session,
                max_tokens=4000,
                temperature=0.7
            ):
                # Accumulate response content from token events
                if event.type == "token" and event.content:
                    response_content += event.content
                
                yield event
            
            # 10. Persist assistant response
            if response_content:
                save_message(
                    actual_conversation_id,
                    user_id,
                    "assistant",
                    response_content,
                    model=request.model,
                    provider=request.provider
                )
                logger.info(f"Saved assistant message to conversation {actual_conversation_id}, length: {len(response_content)}")
            
        except Exception as e:
            logger.error(f"Chat processing error: {e}")
            yield ModelEvent.error(f"Processing error: {str(e)}")
        finally:
            # 11. Cleanup and emit done event
            self.session_manager.stop_streaming(request.sessionId)
            yield ModelEvent.done()
    
    async def _retrieve_rag_context(self, request: ChatRequest) -> RAGResult:
        """Retrieve context from RAGProcessor with validation"""
        if not self.rag_processor:
            return RAGResult.from_context("")
        
        # Retrieve context from RAGProcessor
        context = await asyncio.get_event_loop().run_in_executor(
            None,
            self.rag_processor.retrieve_context,
            request.message,
            request.sessionId,
            3  # top_k
        )
        
        # Apply max context length
        if len(context) > self.max_context_tokens * 4:  # Rough char estimate
            context = context[:self.max_context_tokens * 4] + "\n\n[Context truncated due to length limits]"
        
        return RAGResult.from_context(context)
    
    def _construct_prompt(self, message: str, rag_result: Optional[RAGResult]) -> str:
        """Construct final prompt with anti-hallucination safeguards"""
        if rag_result and rag_result.has_documents:
            # RAG Mode: Include context guard and retrieved documents
            prompt_parts = [
                self.context_guard_message,
                "\n\nCONTEXT:\n",
                rag_result.context,
                "\n\nQUESTION: ",
                message,
                "\n\nANSWER:"
            ]
            return "".join(prompt_parts)
        else:
            # Standard LLM Mode: Just the message
            return message
    
    async def _get_api_key_for_provider(self, provider: str, request: ChatRequest) -> Optional[str]:
        """Get API key for provider"""
        try:
            # This would need integration with user API key storage
            # For now, return None to use provider's default
            return None
        except Exception:
            return None
    
    async def _adapt_legacy_stream(self, provider, request: ChatRequest, api_key: Optional[str]) -> AsyncGenerator[ModelEvent, None]:
        """
        Adapt legacy stream() method to ModelEvent interface.
        This is a temporary adapter until all providers implement stream_chat().
        """
        try:
            # Convert ChatRequest to legacy format
            messages = [{"role": "user", "content": request.message}]
            
            # Get session for HTTP requests
            session = await self.model_registry.get_session()
            
            # Stream using legacy interface
            async for chunk in provider.stream(
                model=request.model,
                messages=messages,
                api_key=api_key or "",
                session=session,
                max_tokens=4000,
                temperature=0.7
            ):
                yield ModelEvent.token(chunk)
            
        except Exception as e:
            logger.error(f"Legacy stream adapter error: {e}")
            yield ModelEvent.error(f"Streaming error: {str(e)}")
    
    async def cancel_chat(self, session_id: str) -> bool:
        """Cancel an active chat session"""
        was_cancelled = self.session_manager.cancel_session(session_id)
        if was_cancelled:
            logger.info(f"Cancelled chat session: {session_id}")
        return was_cancelled
    
    def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """Get status of a chat session"""
        session = self.session_manager.get_session(session_id)
        return {
            "session_id": session_id,
            "is_streaming": session.is_streaming,
            "job_id": session.job_id,
            "created_at": session.created_at.isoformat(),
            "last_activity": session.last_activity.isoformat()
        }


# Global controller instance
_chat_controller = None

def get_chat_controller(rag_processor: Optional[RAGProcessor] = None) -> ChatController:
    """Get global chat controller instance"""
    global _chat_controller
    if _chat_controller is None:
        _chat_controller = ChatController(rag_processor)
    elif rag_processor and not _chat_controller.rag_processor:
        _chat_controller.rag_processor = rag_processor
    return _chat_controller