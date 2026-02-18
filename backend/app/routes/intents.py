"""
Intent Verification Routes
Provides backend verification for message intents
"""

import logging
import re
from fastapi import APIRouter, HTTPException
from typing import Dict, Any

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/intents", tags=["intents"])

@router.post("/verify")
async def verify_intent(prompt: str, type: str) -> Dict[str, Any]:
    """
    Verify message intent for auto-detected actions
    
    Args:
        prompt: User message content
        type: Type of intent to verify ('image', 'document', 'spreadsheet')
    """
    try:
        if type == "image":
            # Enhanced image intent verification
            image_patterns = [
                r"(?:create|generate|make|draw|design|show me|produce|render).*(?:image|picture|photo|illustration|diagram|chart|graph|artwork|painting|sketch)",
                r"(?:an? )?(?:image|picture|photo|illustration|diagram|chart|graph|artwork|painting|sketch) of",
                r"(?:visualize|depict|portray).*",
                r"(?:dalle|midjourney|stable diffusion|ai art|ai image)"
            ]
            
            verified = any(re.search(pattern, prompt.lower()) for pattern in image_patterns)
            
        elif type == "document":
            # Document intent verification
            doc_patterns = [
                r"(?:create|generate|make|write).*(?:document|doc|docx|report|letter|essay|paper|article)",
                r"(?:word document|microsoft word|google docs)"
            ]
            verified = any(re.search(pattern, prompt.lower()) for pattern in doc_patterns)
            
        elif type == "spreadsheet":
            # Spreadsheet intent verification
            spreadsheet_patterns = [
                r"(?:create|generate|make).*(?:spreadsheet|excel|xlsx|table|data|worksheet)",
                r"(?:excel file|google sheets|data table)"
            ]
            verified = any(re.search(pattern, prompt.lower()) for pattern in spreadsheet_patterns)
            
        else:
            verified = False

        return {
            "verified": verified,
            "prompt": prompt,
            "type": type
        }
        
    except Exception as e:
        logger.error(f"Intent verification failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Intent verification failed: {str(e)}")
