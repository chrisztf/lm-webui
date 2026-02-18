"""
Image generation utilities for Gemini
Refactored to use ModelRegistry for secure, non-blocking API calls.
"""
import logging
import base64
from fastapi.responses import JSONResponse
from app.models.schemas import ChatRequest
from app.utils.file_storage import save_image_data, save_file_to_database, link_file_to_message
from app.services.model_registry import get_model_registry
from app.chat.service import save_message, ensure_conversation_exists
from datetime import datetime
import os

logger = logging.getLogger(__name__)

async def generate_image_gemini(req: ChatRequest, background_tasks = None):
    """Generate an image using Gemini/Google image generation models via ModelRegistry"""
    
    # Get user ID and conversation context
    user_id = req.user_id
    conversation_id = req.conversation_id
    
    # Handle user context fallback logic (similar to original)
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
        strategy = registry.get_strategy("google")
        
        if not strategy:
            return JSONResponse(status_code=500, content={"error": "Google provider not available"})
            
        # Resolve API Key
        api_key = req.api_key
        if not api_key:
            user_keys = registry.get_user_api_keys(user_id)
            api_key = user_keys.get("google")
            
        if not api_key:
            return JSONResponse(status_code=401, content={"error": "Google API key required"})
            
        # Get session
        session = await registry.get_session()
        
        # Call generation
        logger.info(f"Generating image with model {req.model}")
        result = await strategy.generate_image(
            model=req.model, 
            prompt=req.message, 
            api_key=api_key, 
            session=session
        )
        
        image_bytes = result["data"]
        mime_type = result.get("mime_type", "image/png")
        
        # Convert to base64 for immediate display
        base64_img = base64.b64encode(image_bytes).decode('utf-8')
        
        # Save image locally (returns URL)
        image_url = await save_image_data(
            image_data=image_bytes,
            conversation_id=conversation_id,
            prompt=req.message,
            model=req.model
        )
        
        # Use Markdown for better compatibility with frontend renderer
        # We use the URL which points to the backend served file
        markdown_response = f"""✅ **Image Generated Successfully!**

I've generated the image for you based on your prompt:

![Generated Image]({image_url})"""

        # Save assistant message
        assistant_msg = save_message(conversation_id, user_id, "assistant", markdown_response)
        
        # Save to media library (database)
        try:
            # Extract filename from URL
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
                file_type=mime_type,
                file_size=len(image_bytes),
                metadata={
                    "model": req.model,
                    "prompt": req.message,
                    "source": "generation"
                }
            )
            
            # Link to message
            await link_file_to_message(file_id, assistant_msg["id"])
            
        except Exception as db_err:
            logger.error(f"Failed to save image metadata to DB: {db_err}")
        
        return {
            "status": "generated",
            "image_url": image_url,
            "message_id": assistant_msg["id"]
        }

    except Exception as e:
        logger.error(f"Gemini image generation error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})
