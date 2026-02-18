"""
Unified Chat Route
Single entry point with ChatGPT-style architecture using ModelRegistry
Implements: UI history ≠ LLM context ≠ Memory ≠ RAG
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Request
from typing import Optional, List, Dict, Any
import logging

from app.security.auth.dependencies import get_current_user
from app.services.chat_service import ChatService
from app.chat.service import (
    save_message,
    should_summarize_conversation,
    get_unsummarized_messages,
    save_conversation_summary
)
from app.memory.summary_layer import generate_conversation_summary_llm
from app.database import get_db
from app.memory.kg_manager import KGManager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat")

# Constants
SUMMARY_THRESHOLD = 500

def extract_file_issues_from_context(context: str) -> List[str]:
    """
    Extract file processing issues from context string.
    Returns list of issue types detected.
    """
    issues = []
    
    # Check for specific error patterns
    if "[File Processing Error" in context:
        issues.append("FILE_PROCESSING_ERROR")
    if "[File Processing Note" in context:
        issues.append("FILE_PROCESSING_NOTE")
    if "[Excel Processing Error" in context:
        issues.append("EXCEL_PROCESSING_ERROR")
    if "[Excel Processing Note" in context:
        issues.append("EXCEL_PROCESSING_NOTE")
    if "[Image Processing Note" in context:
        issues.append("IMAGE_PROCESSING_NOTE")
    if "[Error processing PDF" in context:
        issues.append("PDF_PROCESSING_ERROR")
    if "[Error processing PPTX" in context:
        issues.append("PPTX_PROCESSING_ERROR")
    if "ERROR READING FILE" in context:
        issues.append("ERROR_READING_FILE")
    if "EMPTY FILE" in context:
        issues.append("EMPTY_FILE")
    if "Files with errors" in context:
        issues.append("FILES_WITH_ERRORS")
    if "Files not found" in context:
        issues.append("FILES_NOT_FOUND")
    if "Empty files" in context:
        issues.append("EMPTY_FILES_LIST")
    
    return issues

def build_prompt(
    system_prompt: str,
    conversation_summary: Optional[str],
    user_memory: str,
    last_messages: List[Dict[str, Any]],
    current_message: str,
    rag_context: Optional[str] = None,
    attached_files_context: Optional[str] = None,
    web_search_context: Optional[str] = None
) -> List[Dict[str, str]]:
    """
    Build prompt with new architecture
    """
    messages = []
    
    # System prompt
    messages.append({"role": "system", "content": system_prompt})
    
    # Conversation summary
    if conversation_summary:
        messages.append({"role": "system", "content": f"Conversation summary:\n{conversation_summary}"})
    
    # User memory (Knowledge Graph)
    if user_memory:
        messages.append({"role": "system", "content": f"Relevant User Knowledge:\n{user_memory}"})
        
    # Explicitly Attached Files (Highest Priority Context)
    if attached_files_context:
        messages.append({
            "role": "system", 
            "content": f"USER ATTACHED FILES:\n{attached_files_context}"
        })
        
    # Web Search Results (High Priority Context)
    if web_search_context:
        messages.append({
            "role": "system", 
            "content": f"CURRENT WEB SEARCH RESULTS:\n{web_search_context}"
        })
    
    # General RAG search results (Background Context)
    if rag_context:
        messages.append({"role": "system", "content": f"Background Context (Local Documents):\n{rag_context}"})
    
    # Last N messages
    for msg in last_messages:
        messages.append({"role": msg["role"], "content": msg["content"]})
    
    # Current message
    messages.append({"role": "user", "content": current_message})
    
    return messages

async def generate_conversation_summary_background(conversation_id: str, user_id: int):
    """Background task to generate conversation summary"""
    try:
        messages = get_unsummarized_messages(conversation_id)
        if not messages: return
        
        summary = await generate_conversation_summary_llm(conversation_id, messages, user_id)
        if summary:
            save_conversation_summary(conversation_id, summary)
            logger.info(f"Generated summary for conversation {conversation_id}")
    except Exception as e:
        logger.error(f"Summary generation failed: {e}")

async def generate_and_broadcast_title(
    conversation_id: str,
    user_id: int,
    user_message: str,
    assistant_response: str
):
    """Generate conversation title and broadcast via SSE"""
    try:
        from app.routes.title_updates import broadcast_title_update
        
        # Simple title generation (first 8 words)
        words = user_message.strip().split()
        title = " ".join(words[:8]) + "..." if len(words) > 8 else user_message.strip()
        
        if title:
            db = get_db()
            db.execute(
                "UPDATE conversations SET title = ?, updated_at = ? WHERE id = ? AND user_id = ?",
                (title, datetime.now(), conversation_id, user_id)
            )
            db.commit()
            await broadcast_title_update(conversation_id, title)
            
            try:
                from app.routes.title_updates import notify_title_update_via_websocket
                await notify_title_update_via_websocket(conversation_id, title, user_id)
            except ImportError:
                pass
    except Exception as e:
        logger.error(f"Title generation failed: {str(e)}")

async def generate_llm_title_batch(conversations_data: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """
    Generate titles for multiple conversations using batch processing.
    This can be called from a background task to process multiple conversations in parallel.
    
    Args:
        conversations_data: List of dicts with keys:
            - conversation_id: str
            - user_id: int
            - user_message: str
            - assistant_response: str
            - provider: str (optional, default: "openai")
            - model: str (optional, default: "gpt-4.1-mini")
    
    Returns:
        List of dicts with keys:
            - conversation_id: str
            - title: str
            - success: bool
            - error: str (if failed)
    """
    if not conversations_data:
        return []
    
    try:
        model_registry = get_model_registry()
        results = []
        
        # Group conversations by provider/model for batch processing
        provider_groups = {}
        for conv_data in conversations_data:
            provider = conv_data.get("provider", "openai")
            model = conv_data.get("model", "gpt-4.1-mini")
            key = f"{provider}:{model}"
            
            if key not in provider_groups:
                provider_groups[key] = {
                    "provider": provider,
                    "model": model,
                    "conversations": []
                }
            
            provider_groups[key]["conversations"].append(conv_data)
        
        # Process each provider group in parallel
        async def process_provider_group(provider: str, model: str, conversations: List[Dict[str, Any]]):
            """Process a group of conversations with the same provider/model"""
            try:
                strategy = model_registry.get_strategy(provider)
                if not strategy:
                    return [{
                        "conversation_id": conv["conversation_id"],
                        "title": "",
                        "success": False,
                        "error": f"Unsupported provider: {provider}"
                    } for conv in conversations]
                
                # Get API key for the first conversation (assuming same user)
                user_id = conversations[0]["user_id"]
                user_keys = model_registry.get_user_api_keys(user_id)
                api_key = user_keys.get(provider) or user_keys.get(strategy.get_backend_name())
                
                session = await model_registry.get_session()
                
                # Prepare batch prompts
                batch_prompts = []
                for conv in conversations:
                    prompt = f"""Generate a concise, descriptive title (max 8 words) for this conversation:
                    
                    User: {conv['user_message'][:200]}
                    Assistant: {conv['assistant_response'][:200]}
                    
                    Title:"""
                    batch_prompts.append(prompt)
                
                # Use batch endpoint if available, otherwise process sequentially
                try:
                    # Try to use batch processing
                    batch_results = await strategy.generate_batch(
                        model=model,
                        messages_list=[[{"role": "user", "content": prompt}] for prompt in batch_prompts],
                        api_key=api_key,
                        session=session
                    )
                    
                    # Process batch results
                    group_results = []
                    for i, conv in enumerate(conversations):
                        if i < len(batch_results):
                            title = batch_results[i].strip()
                            # Clean up title
                            title = title.replace('"', '').replace("'", "").strip()
                            if len(title) > 100:
                                title = title[:97] + "..."
                            
                            group_results.append({
                                "conversation_id": conv["conversation_id"],
                                "title": title,
                                "success": True,
                                "error": ""
                            })
                        else:
                            group_results.append({
                                "conversation_id": conv["conversation_id"],
                                "title": "",
                                "success": False,
                                "error": "Batch result missing"
                            })
                    
                    return group_results
                    
                except (AttributeError, NotImplementedError):
                    # Fallback to sequential processing
                    logger.warning(f"Batch processing not available for {provider}, falling back to sequential")
                    group_results = []
                    
                    for conv in conversations:
                        try:
                            title_response = await strategy.generate(
                                model=model,
                                messages=[{"role": "user", "content": f"Generate a concise, descriptive title (max 8 words) for this conversation:\n\nUser: {conv['user_message'][:200]}\nAssistant: {conv['assistant_response'][:200]}\n\nTitle:"}],
                                api_key=api_key,
                                session=session
                            )
                            
                            title = title_response.strip()
                            title = title.replace('"', '').replace("'", "").strip()
                            if len(title) > 100:
                                title = title[:97] + "..."
                            
                            group_results.append({
                                "conversation_id": conv["conversation_id"],
                                "title": title,
                                "success": True,
                                "error": ""
                            })
                        except Exception as e:
                            logger.error(f"Title generation failed for conversation {conv['conversation_id']}: {e}")
                            group_results.append({
                                "conversation_id": conv["conversation_id"],
                                "title": "",
                                "success": False,
                                "error": str(e)
                            })
                    
                    return group_results
                    
            except Exception as e:
                logger.error(f"Provider group processing failed: {e}")
                return [{
                    "conversion_id": conv["conversation_id"],
                    "title": "",
                    "success": False,
                    "error": f"Group processing failed: {str(e)}"
                } for conv in conversations]
        
        # Process all provider groups in parallel
        tasks = []
        for key, group in provider_groups.items():
            task = process_provider_group(
                group["provider"],
                group["model"],
                group["conversations"]
            )
            tasks.append(task)
        
        # Run all provider groups in parallel
        group_results_list = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Flatten results
        for group_results in group_results_list:
            if isinstance(group_results, list):
                results.extend(group_results)
            elif isinstance(group_results, Exception):
                logger.error(f"Task failed with exception: {group_results}")
                # Add error results for all conversations in the failed group
                # We need to track which conversations were in which group
                # For simplicity, we'll mark all as failed
                pass
        
        return results
        
    except Exception as e:
        logger.error(f"Batch title generation failed: {e}")
        return [{
            "conversation_id": conv_data["conversation_id"],
            "title": "",
            "success": False,
            "error": f"System error: {str(e)}"
        } for conv_data in conversations_data]

@router.post("")
async def chat_completion(
    request: dict,
    raw_request: Request,
    background_tasks: BackgroundTasks,
    user_id: dict = Depends(get_current_user)
):
    """
    Single chat completion endpoint using ModelRegistry and new RAG/KG
    Simplified version using ChatService abstraction
    """
    # Lazy load components from app state
    rag_processor = getattr(raw_request.app.state, "rag_processor", None)
    kg_manager = getattr(raw_request.app.state, "kg_manager", None)
    
    # DEBUG: Log all received parameters
    logger.debug(f"📡 Chat request received: {request}")
    
    message = request.get("message", "")
    provider = request.get("provider", "openai")
    model = request.get("model", "gpt-4.1-mini")
    client_api_key = request.get("api_key") 
    conversation_id = request.get("conversation_id")
    show_raw_response = request.get("show_raw_response", False)
    deep_thinking_mode = request.get("deep_thinking_mode", False)
    use_rag = request.get("use_rag", True)
    file_references = request.get("file_references", [])
    web_search = request.get("web_search", False)
    search_provider = request.get("search_provider", "duckduckgo")
    
    # DEBUG: Log conversation_id specifically
    logger.debug(f"📡 conversation_id from request: {conversation_id}")
    logger.debug(f"📡 user_id from auth: {user_id}")
    
    # DEBUG: Log all keys in request to see what's actually being sent
    logger.debug(f"📡 All request keys: {list(request.keys())}")
    
    if not message:
        raise HTTPException(400, "Message is required")
    
    user_id_int = user_id["id"]
    
    try:
        # Create chat service instance
        chat_service = ChatService(rag_processor=rag_processor, kg_manager=kg_manager)
        
        # Process chat completion using the service abstraction
        result = await chat_service.process_chat_completion(
            message=message,
            provider=provider,
            model=model,
            client_api_key=client_api_key,
            conversation_id=conversation_id,
            user_id=user_id_int,
            show_raw_response=show_raw_response,
            deep_thinking_mode=deep_thinking_mode,
            use_rag=use_rag,
            file_references=file_references,
            web_search=web_search,
            search_provider=search_provider
        )
        
        # Add background tasks
        if kg_manager:
            # Update Knowledge Graph in background
            from app.chat.service import get_last_n_messages
            last_messages = get_last_n_messages(result["conversation_id"], n=5)
            full_history = last_messages + [{"role": "assistant", "content": result["response"]}]
            background_tasks.add_task(kg_manager.extract_and_store_knowledge, result["conversation_id"], full_history, user_id_int)
            
        if should_summarize_conversation(result["conversation_id"], threshold=SUMMARY_THRESHOLD):
            background_tasks.add_task(generate_conversation_summary_background, result["conversation_id"], user_id_int)
        
        return result
        
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error(f"Generation error: {e}")
        raise HTTPException(500, f"LLM error: {str(e)}")
