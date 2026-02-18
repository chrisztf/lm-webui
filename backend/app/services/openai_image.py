"""
Image generation utilities for OpenAI
Refactored to use ModelRegistry for secure, non-blocking API calls.
"""
import logging
import json
from datetime import datetime
from fastapi.responses import JSONResponse
from app.models.schemas import ChatRequest
from app.utils.file_storage import save_image_data, save_file_to_database, link_file_to_message
from app.services.model_registry import get_model_registry
from app.chat.service import save_message, ensure_conversation_exists
from app.database import get_db
import os

logger = logging.getLogger(__name__)

async def generate_image_openai(req: ChatRequest, background_tasks = None):
    """Generate an image using OpenAI models via ModelRegistry"""
    
    # Get user ID and conversation context
    user_id = req.user_id
    conversation_id = req.conversation_id
    
    # Handle user context fallback logic
    if not user_id and hasattr(req, 'user') and req.user:
        user_id = req.user.get("id")
        
    if not conversation_id:
        conversation_id = f"conv_{int(datetime.now().timestamp() * 1000)}"
        
    if not user_id:
        return JSONResponse(status_code=400, content={"error": "User ID required"})

    try:
        # Save user message first
        ensure_conversation_exists(conversation_id, user_id)
        save_message(conversation_id, user_id, "user", req.message)
        
        # Use ModelRegistry
        registry = get_model_registry()
        strategy = registry.get_strategy("openai")
        
        if not strategy:
            return JSONResponse(status_code=500, content={"error": "OpenAI provider not available"})
            
        # Resolve API Key
        api_key = req.api_key
        if not api_key:
            user_keys = registry.get_user_api_keys(user_id)
            api_key = user_keys.get("openai")
            
        if not api_key:
            return JSONResponse(status_code=401, content={"error": "OpenAI API key required"})
            
        # Get session
        session = await registry.get_session()
        
        # Call generation
        logger.info(f"Generating image with model {req.model}")
        
        # Map quality settings
        quality = "standard"
        if "hd" in req.model.lower():
            quality = "hd"
            
        result = await strategy.generate_image(
            model=req.model.replace("-hd", "").replace("-standard", ""), # Strip suffixes if present
            prompt=req.message, 
            api_key=api_key, 
            session=session,
            quality=quality,
            size=req.size or "1024x1024"
        )
        
        image_bytes = result["data"]
        
        # Save image locally (returns URL)
        image_url = await save_image_data(
            image_data=image_bytes,
            conversation_id=conversation_id,
            prompt=req.message,
            model=req.model
        )
        
        # Use Markdown for better compatibility
        markdown_response = f"""✅ **Image Generated Successfully!**

I've generated the image for you based on your prompt:

![Generated Image]({image_url})"""

        assistant_msg = save_message(conversation_id, user_id, "assistant", markdown_response)
        
        # Save to media library (database) and link
        try:
            filename = image_url.split('/')[-1]
            
            # Determine physical path matching file_storage.py logic
            base_media_path = os.getenv("MEDIA_DIR")
            if not base_media_path:
                if os.path.exists("backend/media"):
                    media_dir = "backend/media"
                elif os.path.exists("media"):
                    media_dir = "media"
                else:
                    media_dir = "backend/media"
            else:
                media_dir = base_media_path
                
            physical_path = os.path.join(media_dir, "generated", "images", filename)
            
            file_id = await save_file_to_database(
                user_id=user_id,
                conversation_id=conversation_id,
                filename=filename,
                file_path=physical_path,
                file_type="image/png", # OpenAI usually returns PNG via base64 or URL
                file_size=len(image_bytes),
                metadata={
                    "model": req.model,
                    "prompt": req.message,
                    "source": "generation"
                }
            )
            
            await link_file_to_message(file_id, assistant_msg["id"])
            
        except Exception as db_err:
            logger.error(f"Failed to save image metadata to DB: {db_err}")
        
        return {
            "status": "generated",
            "image_url": image_url,
            "message_id": assistant_msg["id"]
        }

    except Exception as e:
        logger.error(f"OpenAI image generation error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})
