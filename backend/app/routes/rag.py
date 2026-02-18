"""
RAG Routes
Handles RAG (Retrieval-Augmented Generation) operations including OCR and vision processing
Updated to use new RAGProcessor
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
# from app.rag.processor import unified_processor # Legacy
from app.rag.processor import RAGProcessor
import logging
import tempfile
import os

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/rag", tags=["rag"])

# Initialize RAG Processor
try:
    rag_processor = RAGProcessor()
except Exception as e:
    logger.error(f"Failed to init RAGProcessor in rag routes: {e}")
    rag_processor = None

@router.post("/ocr")
async def process_ocr(file: UploadFile = File(...)):
    """
    Process OCR on uploaded file
    
    Returns extracted text as markdown code block
    """
    try:
        # Validate file type
        allowed_extensions = ['.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.tif']
        file_extension = os.path.splitext(file.filename)[1].lower()
        
        if file_extension not in allowed_extensions:
            raise HTTPException(
                400, 
                f"Unsupported file type: {file_extension}. Supported types: {allowed_extensions}"
            )
        
        if not rag_processor:
             raise HTTPException(500, "RAG system not initialized")

        # Save uploaded file to temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_path = temp_file.name
        
        try:
            # Process file with RAG Processor (OCR fallback happens internally if image)
            # RAGProcessor.process_file expects conversation_id, use "ocr_request"
            result = rag_processor.process_file(temp_path, conversation_id="ocr_request")
            
            if result.get("status") != "success":
                raise HTTPException(500, f"OCR processing failed: {result.get('message', 'Unknown error')}")
            
            # Extract text content
            text_content = result.get("extracted_text", "").strip()
            
            if not text_content:
                return {
                    "success": True,
                    "content": "```text\nNo text could be extracted from the document.\n```",
                    "has_text": False,
                    "confidence": 0
                }
            
            # Format as markdown code block
            formatted_content = f"```text\n{text_content}\n```"
            
            return {
                "success": True,
                "content": formatted_content,
                "has_text": True,
                "confidence": 1.0, # Placeholder
                "file_info": {"filename": file.filename},
                "analysis": {}
            }
            
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_path)
            except:
                pass
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OCR endpoint error: {str(e)}")
        raise HTTPException(500, f"OCR processing error: {str(e)}")

@router.post("/vision")
async def process_vision(file: UploadFile = File(...)):
    """
    Process image with vision model
    
    Returns image description as markdown code block
    """
    try:
        # Validate file type
        allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif']
        file_extension = os.path.splitext(file.filename)[1].lower()
        
        if file_extension not in allowed_extensions:
            raise HTTPException(
                400, 
                f"Unsupported image type: {file_extension}. Supported types: {allowed_extensions}"
            )
            
        if not rag_processor:
             raise HTTPException(500, "RAG system not initialized")
        
        # Save uploaded file to temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_path = temp_file.name
        
        try:
            # Process image with vision model
            result = rag_processor.process_file(temp_path, conversation_id="vision_request")
            
            if result.get("status") != "success":
                raise HTTPException(500, f"Vision processing failed: {result.get('message', 'Unknown error')}")
            
            # Extract vision description
            vision_description = result.get("extracted_text", "").strip()
            
            if not vision_description:
                return {
                    "success": True,
                    "content": "```text\nNo description could be generated for this image.\n```",
                    "has_description": False,
                    "model": "moondream2"
                }
            
            # Format as markdown code block
            formatted_content = f"```text\nImage Description:\n{vision_description}\n```"
            
            return {
                "success": True,
                "content": formatted_content,
                "has_description": True,
                "model": "moondream2",
                "file_info": {"filename": file.filename},
                "analysis": {}
            }
            
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_path)
            except:
                pass
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Vision endpoint error: {str(e)}")
        raise HTTPException(500, f"Vision processing error: {str(e)}")

@router.get("/status")
async def get_rag_status():
    """
    Get status of RAG processing capabilities
    """
    try:
        return {
            "status": "ready" if rag_processor else "error",
            "ocr_available": True, # EasyOCR fallback
            "vision_available": True, # Moondream
            "vision_model": "moondream2",
            "supported_extensions": ['.pdf', '.jpg', '.jpeg', '.png', '.docx', '.txt'],
            "max_file_size_mb": 100
        }
        
    except Exception as e:
        logger.error(f"Status check error: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "ocr_available": False,
            "vision_available": False,
            "vision_model": None
        }
