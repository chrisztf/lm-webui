"""
Image Generation Routes
Handles AI image generation functionality for multiple providers.
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
import logging
import os

from app.security.auth.dependencies import get_current_user
from app.services.openai_image import generate_image_openai
from app.services.gemini_image import generate_image_gemini
from app.models.schemas import ChatRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/images", tags=["images"])

async def _prepare_image_request(request: dict, user_id: dict, provider: str) -> ChatRequest:
    """Helper function to prepare the ChatRequest for image generation."""
    prompt = request.get("prompt", "")
    if not prompt:
        raise HTTPException(400, "Prompt is required for image generation")

    return ChatRequest(
        message=prompt,
        provider=provider,
        model=request.get("model"),
        api_key=request.get("api_key"),
        size=request.get("size", "1024x1024"),
        quality=request.get("quality", "standard"),
        style=request.get("style", "vivid"),
        user_id=user_id["id"],
        conversation_id=request.get("conversation_id")
    )

@router.post("/generate/openai")
async def generate_openai_image(
    request: dict, 
    background_tasks: BackgroundTasks,
    user_id: dict = Depends(get_current_user)
):
    """Generate image using OpenAI models."""
    try:
        image_request = await _prepare_image_request(request, user_id, "openai")
        result = await generate_image_openai(image_request, background_tasks)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OpenAI image generation error: {str(e)}")
        raise HTTPException(500, f"OpenAI image generation error: {str(e)}")

@router.post("/generate/google")
@router.post("/generate/gemini")
async def generate_google_image(
    request: dict, 
    background_tasks: BackgroundTasks,
    user_id: dict = Depends(get_current_user)
):
    """Generate image using Google (Gemini) models."""
    try:
        # Standardize on "google" provider
        image_request = await _prepare_image_request(request, user_id, "google")
        result = await generate_image_gemini(image_request, background_tasks)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Google image generation error: {str(e)}")
        raise HTTPException(500, f"Google image generation error: {str(e)}")

@router.get("/models")
async def get_image_models(user_id: dict = Depends(get_current_user)):
    """Get available image generation models for all providers."""
    try:
        openai_models = [
            "dall-e-2",
            "dall-e-3",
        ]
        google_models = [
            "gemini-2.5-flash-image", # Nano Banana
            "gemini-3-pro-image-preview", # Nano Banana Pro
            "imagen-3" 
        ]

        return {
            "success": True,
            "models": {
                "openai": openai_models,
                "google": google_models,
                "gemini": google_models # Backward compatibility
            }
        }
    except Exception as e:
        logger.error(f"Failed to get image models: {str(e)}")
        raise HTTPException(500, f"Failed to get image models: {str(e)}")

@router.get("/status")
async def image_generation_status():
    """Get image generation service status."""
    try:
        openai_key = os.getenv("OPENAI_API_KEY")
        google_key = os.getenv("GOOGLE_API_KEY")
        
        return {
            "status": "ready" if openai_key or google_key else "missing_api_key",
            "providers": {
                "openai": "ready" if openai_key else "missing_key",
                "google": "ready" if google_key else "missing_key"
            }
        }
    except Exception as e:
        logger.error(f"Failed to get image generation status: {str(e)}")
        raise HTTPException(500, f"Failed to get image generation status: {str(e)}")

@router.get("/health")
async def health_check():
    """Health check for image generation services."""
    try:
        openai_key = os.getenv("OPENAI_API_KEY")
        google_key = os.getenv("GOOGLE_API_KEY")
        
        return {
            "status": "healthy" if openai_key or google_key else "unhealthy",
            "services": {
                "openai_dalle": "ready" if openai_key else "missing_key",
                "google_imagen": "ready" if google_key else "missing_key",
                "image_processing": "ready"
            }
        }
    except Exception as e:
        logger.error(f"Image generation health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }
