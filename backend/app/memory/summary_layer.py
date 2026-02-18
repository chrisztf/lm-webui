"""
Summary Layer - Handles conversation summarization for LLM context
Implements the conversation_summaries table operations
"""

import datetime
import logging
import json
import os
import asyncio
from typing import Optional, List, Dict, Any
from functools import partial
from app.database import get_db
from app.memory.kg_manager import KGManager
from app.hardware.detection import get_llamacpp_settings

logger = logging.getLogger(__name__)

# Initialize KGManager (Using correct path: data/memory/memory.db)
try:
    import os
    data_dir = os.getenv("DATA_DIR")
    if data_dir:
        if os.path.isabs(data_dir):
             mem_path = os.path.join(data_dir, "memory", "memory.db")
        else:
             base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
             mem_path = os.path.join(base_dir, data_dir, "memory", "memory.db")
    else:
         base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
         mem_path = os.path.join(base_dir, "data", "memory", "memory.db")
         
    kg_manager = KGManager(mem_path)
except Exception as e:
    logger.error(f"Failed to initialize KGManager in summary_layer: {e}")
    kg_manager = None

# Constants
MODEL_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../models/Qwen3-0.6B-Q6_K.gguf"))

def get_conversation_summary(conversation_id: str) -> Optional[str]:
    """
    Get conversation summary from conversation_summaries table
    
    Args:
        conversation_id: Conversation ID
        
    Returns:
        Summary text or None if not found
    """
    db = get_db()
    result = db.execute(
        "SELECT summary FROM conversation_summaries WHERE conversation_id = ?",
        (conversation_id,)
    ).fetchone()
    
    return result[0] if result else None

def save_conversation_summary(conversation_id: str, summary: str) -> bool:
    """
    Save or update conversation summary
    
    Args:
        conversation_id: Conversation ID
        summary: Summary text
        
    Returns:
        Success status
    """
    try:
        db = get_db()
        db.execute(
            "INSERT OR REPLACE INTO conversation_summaries (conversation_id, summary, updated_at) VALUES (?, ?, ?)",
            (conversation_id, summary, datetime.datetime.now())
        )
        db.commit()
        logger.info(f"✅ Saved summary for conversation {conversation_id}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to save summary for conversation {conversation_id}: {str(e)}")
        return False

def delete_conversation_summary(conversation_id: str) -> bool:
    """
    Delete conversation summary
    
    Args:
        conversation_id: Conversation ID
        
    Returns:
        Success status
    """
    try:
        db = get_db()
        db.execute(
            "DELETE FROM conversation_summaries WHERE conversation_id = ?",
            (conversation_id,)
        )
        db.commit()
        logger.info(f"✅ Deleted summary for conversation {conversation_id}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to delete summary for conversation {conversation_id}: {str(e)}")
        return False

def should_summarize_conversation(conversation_id: str, threshold: int = 6) -> bool:
    """
    Check if conversation should be summarized based on message count.
    Legacy implementation used by direct callers if they exist.
    """
    try:
        db = get_db()
        result = db.execute(
            "SELECT message_count FROM conversations WHERE id = ?",
            (conversation_id,)
        ).fetchone()
        
        if not result:
            return False
        
        message_count = result[0]
        return message_count > 0 and message_count % threshold == 0
    except Exception as e:
        logger.error(f"❌ Failed to check summarization for conversation {conversation_id}: {str(e)}")
        return False

def get_recent_messages_for_summarization(conversation_id: str, limit: int = 20) -> List[Dict[str, Any]]:
    """
    Get recent messages for summarization.
    Legacy/Fallback implementation.
    """
    try:
        db = get_db()
        messages = db.execute(
            "SELECT role, content FROM messages WHERE conversation_id = ? ORDER BY created_at DESC LIMIT ?",
            (conversation_id, limit)
        ).fetchall()
        
        # Return in chronological order
        return [
            {"role": msg[0], "content": msg[1]}
            for msg in reversed(messages)
        ]
    except Exception as e:
        logger.error(f"❌ Failed to get messages for summarization: {str(e)}")
        return []

async def generate_conversation_summary_llm(conversation_id: str, messages: List[Dict[str, Any]], user_id: int) -> Optional[str]:
    """
    Generate conversation summary using LLM with rolling update logic
    
    Args:
        conversation_id: Conversation ID
        messages: List of NEW messages to summarize
        user_id: User ID for context retrieval
        
    Returns:
        Generated summary or None if failed
    """
    if not messages:
        return None
    
    try:
        # Get existing summary
        old_summary = get_conversation_summary(conversation_id)
        
        # Get Knowledge Graph context
        kg_nodes = []
        if kg_manager:
            # Use get_all_memories for compatibility with what summary layer expects (list of dicts)
            kg_nodes = kg_manager.get_all_memories(user_id, limit=20)
            
        kg_context = "\n".join([f"- {node.get('content', '')}" for node in kg_nodes])
        
        # Build conversation text
        new_conversation_text = ""
        for msg in messages:
            speaker = "User" if msg["role"] == "user" else "Assistant"
            new_conversation_text += f"{speaker}: {msg['content']}\n\n"
        
        if os.path.exists(MODEL_PATH):
            try:
                def run_gguf_summary(prompt_text, m_path):
                    try:
                        from llama_cpp import Llama
                        
                        settings = get_llamacpp_settings()
                        
                        llm = Llama(
                            model_path=m_path,
                            n_ctx=4096,
                            n_threads=settings["n_threads"],
                            n_gpu_layers=settings["n_gpu_layers"],
                            verbose=False,
                            use_mmap=settings.get("use_mmap", True),
                            use_mlock=settings.get("use_mlock", False)
                        )
                        output = llm(
                            prompt_text,
                            max_tokens=300,
                            stop=["<|im_end|>", "User:", "System:"],
                            temperature=0.3,
                            echo=False
                        )
                        return output["choices"][0]["text"].strip()
                    except Exception as e:
                        logger.error(f"❌ GGUF inference internal error: {e}")
                        return None
                
                # Construct Rolling Prompt
                prompt = f"""Update the conversation summary with new events.
                
                Global Context (Knowledge Graph):
                {kg_context}
                
                Current Summary:
                {old_summary if old_summary else "No previous summary."}
                
                New Messages:
                {new_conversation_text}
                
                Instructions:
                1. Update the Current Summary to include key events from New Messages.
                2. Maintain a coherent narrative flow.
                3. Do NOT repeat facts already present in Global Context (e.g. "User likes Python").
                4. Focus on actions, decisions, and current topic status.
                
                Updated Summary:"""

                formatted_prompt = f"<|start_header_id|>system<|end_header_id|>\n\nYou are a concise summarizer.<|eot_id|><|start_header_id|>user<|end_header_id|>\n\n{prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n"
                
                loop = asyncio.get_running_loop()
                summary = await loop.run_in_executor(None, partial(run_gguf_summary, formatted_prompt, MODEL_PATH))
                
                if summary:
                    logger.info(f"✅ Generated Rolling Summary for {conversation_id}")
                    return summary
                
            except Exception as gguf_error:
                logger.error(f"❌ GGUF summarization failed: {gguf_error}")
        
        # Fallback
        logger.warning("GGUF summary failed, returning None to retry later.")
        return None
        
    except Exception as e:
        logger.error(f"❌ Failed to generate summary: {str(e)}")
        return None

def get_conversation_summary_history(conversation_id: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Get summary history for a conversation (if we store multiple versions)
    
    Args:
        conversation_id: Conversation ID
        limit: Maximum number of historical summaries
        
    Returns:
        List of summaries with timestamps
    """
    # Note: Current schema only stores one summary per conversation
    # This function is for future expansion
    summary = get_conversation_summary(conversation_id)
    if not summary:
        return []
    
    return [{
        "summary": summary,
        "updated_at": datetime.datetime.now().isoformat(),
        "version": "current"
    }]

def update_summary_from_new_message(conversation_id: str, new_message: Dict[str, Any]) -> bool:
    """
    Update summary incrementally based on new message
    This is more efficient than regenerating from scratch
    
    Args:
        conversation_id: Conversation ID
        new_message: New message to incorporate
        
    Returns:
        Success status
    """
    try:
        current_summary = get_conversation_summary(conversation_id)
        
        if not current_summary:
            # No existing summary, create initial one when we have enough messages
            return False
        
        # TODO: Implement incremental summary update
        # For now, we'll rely on periodic full regeneration
        return False
    except Exception as e:
        logger.error(f"❌ Failed to update summary incrementally: {str(e)}")
        return False
