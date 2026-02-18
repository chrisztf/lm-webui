"""EasyOCR wrapper with fallback."""
try:
    import easyocr
except ImportError:
    easyocr = None
    print("Warning: easyocr not installed. OCR functionality will be unavailable.")

import torch
from typing import Optional
import os
from app.hardware.detection import detect_hardware

class OCRProcessor:
    def __init__(self):
        self.reader = None
        self.easyocr_available = easyocr is not None

    def _initialize_reader(self):
        """Lazy load EasyOCR reader"""
        if self.easyocr_available and self.reader is None:
            try:
                # Auto-detect hardware
                hardware = detect_hardware()
                backend = hardware.get("backend", "cpu")
                
                # EasyOCR currently mostly supports CUDA for 'gpu=True'
                # MPS/ROCm support varies by version/build.
                # We enable GPU if backend is CUDA or ROCm.
                # For Metal/SYCL, we might fallback to CPU for stability unless explicit support is verified.
                use_gpu = backend in ["cuda", "rocm"]
                
                # Ensure directory exists
                model_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../rag/ocr"))
                os.makedirs(model_dir, exist_ok=True)
                
                self.reader = easyocr.Reader(
                    ['en'], 
                    gpu=use_gpu,
                    model_storage_directory=model_dir
                )
                print(f"OCR Processor initialized (Backend: {backend}, GPU Used: {use_gpu})")
            except Exception as e:
                print(f"Failed to initialize EasyOCR: {e}")
                self.reader = None
    
    def extract_text(self, image_path: str) -> str:
        """Extract text from image using OCR."""
        # Lazy load
        if self.reader is None:
            self._initialize_reader()

        if not self.reader:
            return ""
            
        try:
            results = self.reader.readtext(image_path)
            text = "\n".join([result[1] for result in results])
            return text
        except Exception as e:
            print(f"OCR failed: {e}")
            return ""
