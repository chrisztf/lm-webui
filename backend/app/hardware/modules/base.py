"""
Base backend interface for hardware acceleration
All backend implementations must inherit from this class
"""
import logging
from abc import ABC, abstractmethod
from typing import Dict, Optional, Any, List
from pathlib import Path

logger = logging.getLogger(__name__)

class BackendRunner(ABC):
    """Abstract base class for hardware backend runners"""
    
    def __init__(self):
        self._loaded_models = {}
        
    @staticmethod
    @abstractmethod
    def is_available() -> bool:
        """
        Check if this backend is available on the current system
        
        Returns:
            True if backend is available, False otherwise
        """
        pass
    
    @abstractmethod
    def load_model(self, model_path: str, quant: str, **kwargs) -> Any:
        """
        Load a model for inference
        
        Args:
            model_path: Path to model file
            quant: Quantization type
            **kwargs: Additional backend-specific parameters
            
        Returns:
            Model handle for inference
        """
        pass
    
    @abstractmethod
    def run_inference(self, model_handle: Any, prompt: str, **kwargs) -> str:
        """
        Run inference on a loaded model
        
        Args:
            model_handle: Model handle from load_model
            prompt: Input prompt
            **kwargs: Additional inference parameters
            
        Returns:
            Generated text
        """
        pass
    
    @abstractmethod
    def unload_model(self, model_handle: Any) -> None:
        """
        Unload a model and free resources
        
        Args:
            model_handle: Model handle to unload
        """
        pass
    
    def probe_model_requirements(self, model_path: str) -> Dict[str, Any]:
        """
        Probe model requirements (size, suggested quants, etc.)
        
        Args:
            model_path: Path to model file
            
        Returns:
            Dictionary with model requirements
        """
        try:
            model_size_bytes = Path(model_path).stat().st_size
            model_size_mb = model_size_bytes / (1024 * 1024)
            
            # Import here to avoid circular imports
            from ..quantization import extract_quant_from_filename, recommended_quants_for_backend
            
            quant = extract_quant_from_filename(model_path)
            backend_name = self.__class__.__name__.replace('Backend', '').lower()
            suggested_quants = recommended_quants_for_backend(backend_name)
            
            return {
                "size_mb": int(model_size_mb),
                "suggested_quants": suggested_quants,
                "quant": quant,
                "estimated_vram_mb": int(model_size_mb * 2.0)  # Conservative 2x estimate
            }
        except Exception as e:
            logger.warning(f"Could not probe model requirements: {e}")
            return {
                "size_mb": 0,
                "suggested_quants": [],
                "quant": "unknown",
                "estimated_vram_mb": 0
            }
    
    def check_vram_compatibility(self, model_path: str, available_vram_mb: int) -> Dict[str, Any]:
        """
        Check if model fits in available VRAM
        
        Args:
            model_path: Path to model file
            available_vram_mb: Available VRAM in MB
            
        Returns:
            Dictionary with compatibility information
        """
        requirements = self.probe_model_requirements(model_path)
        estimated_vram = requirements["estimated_vram_mb"]
        
        fits_vram = estimated_vram <= available_vram_mb
        vram_ratio = estimated_vram / available_vram_mb if available_vram_mb > 0 else float('inf')
        
        return {
            "fits_vram": fits_vram,
            "estimated_vram_mb": estimated_vram,
            "available_vram_mb": available_vram_mb,
            "vram_ratio": vram_ratio,
            "recommendation": "use" if fits_vram else "fallback",
            "message": f"Model requires ~{estimated_vram}MB VRAM, {available_vram_mb}MB available"
        }
