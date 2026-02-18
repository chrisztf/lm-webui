"""
Quantization mapping and helper functions for hardware backends
Provides recommended quantizations and fallback logic
"""
import re
import logging
from typing import List, Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class QuantizationManager:
    """Manages quantization recommendations and fallback logic"""
    
    # Quantization hierarchy from highest to lowest quality
    QUANT_HIERARCHY = {
        'metal': ['Q8_K_M', 'Q6_K', 'Q5_K_M', 'Q4_K_M', 'Q4_K_S', 'Q4_0'],
        'cuda': ['Q8_K_M', 'Q6_K', 'Q5_K_M', 'Q4_K_M', 'Q4_K_S', 'Q4_0'],
        'rocm': ['Q8_K_M', 'Q6_K', 'Q5_K_M', 'Q4_K_M', 'Q4_K_S', 'Q4_0'],
        'cpu': ['Q4_K_S', 'Q4_0', 'Q5_K_S', 'Q5_K_M', 'Q6_K', 'Q8_K_M']
    }
    
    # VRAM requirements per quantization (rough estimates in MB per billion parameters)
    VRAM_REQUIREMENTS = {
        'Q8_K_M': 8500,   # ~8.5GB per billion params
        'Q6_K': 6500,     # ~6.5GB per billion params
        'Q5_K_M': 5500,   # ~5.5GB per billion params
        'Q4_K_M': 4500,   # ~4.5GB per billion params
        'Q4_K_S': 4000,   # ~4.0GB per billion params
        'Q4_0': 3800,     # ~3.8GB per billion params
        'FP16': 2000,     # ~2.0GB per billion params
        'BF16': 2000      # ~2.0GB per billion params
    }
    
    def __init__(self):
        pass
    
    def recommended_quants_for_backend(self, backend: str) -> List[str]:
        """
        Get recommended quantizations for a specific backend
        
        Args:
            backend: One of 'cpu', 'cuda', 'rocm', 'metal'
            
        Returns:
            List of recommended quantization types
        """
        return self.QUANT_HIERARCHY.get(backend, self.QUANT_HIERARCHY['cpu']).copy()
    
    def pick_best_quant(self, model_quant: str, backend: str, vram_mb: int, model_params: Optional[int] = None) -> str:
        """
        Pick the best quantization for a model based on backend and available VRAM
        
        Args:
            model_quant: Current model quantization
            backend: Target backend
            vram_mb: Available VRAM in MB
            model_params: Number of model parameters (optional)
            
        Returns:
            Best quantization type to use
        """
        # If model quantization is already optimal, use it
        if self._is_quant_supported(model_quant, backend):
            # Check if it fits in VRAM
            if self._quant_fits_vram(model_quant, vram_mb, model_params):
                return model_quant
        
        # Find the best supported quantization that fits in VRAM
        recommended_quants = self.recommended_quants_for_backend(backend)
        
        for quant in recommended_quants:
            if self._is_quant_supported(quant, backend) and self._quant_fits_vram(quant, vram_mb, model_params):
                logger.info(f"Selected quantization {quant} for backend {backend} with {vram_mb}MB VRAM")
                return quant
        
        # Fallback to CPU-safe quantization if nothing fits
        cpu_quants = self.recommended_quants_for_backend('cpu')
        for quant in cpu_quants:
            if self._quant_fits_vram(quant, vram_mb, model_params):
                logger.warning(f"Fallback to CPU-safe quantization {quant} due to VRAM constraints")
                return quant
        
        # Final fallback - use the lightest quantization
        logger.warning(f"Using fallback quantization Q4_0 due to VRAM constraints")
        return "Q4_0"
    
    def _is_quant_supported(self, quant: str, backend: str) -> bool:
        """Check if quantization is supported by backend"""
        if backend == 'cpu':
            # CPU supports all quantizations but prefers lighter ones
            return True
        elif backend in ['cuda', 'rocm', 'metal']:
            # GPU backends support all standard quantizations
            return quant in self.VRAM_REQUIREMENTS
        return False
    
    def _quant_fits_vram(self, quant: str, vram_mb: int, model_params: Optional[int] = None) -> bool:
        """Check if quantization fits in available VRAM"""
        if model_params is None:
            # Without model params, assume it fits (conservative)
            return True
            
        # Estimate VRAM usage
        params_billions = model_params / 1_000_000_000
        vram_required = self.VRAM_REQUIREMENTS.get(quant, 5000) * params_billions
        
        # Add 20% buffer for overhead
        vram_required_with_buffer = vram_required * 1.2
        
        return vram_required_with_buffer <= vram_mb
    
    def estimate_model_vram(self, model_path: str, quant: Optional[str] = None) -> int:
        """
        Estimate VRAM usage for a model
        
        Args:
            model_path: Path to model file
            quant: Quantization type (if None, extracted from filename)
            
        Returns:
            Estimated VRAM usage in MB
        """
        try:
            # Get model file size
            model_size_bytes = Path(model_path).stat().st_size
            model_size_mb = model_size_bytes / (1024 * 1024)
            
            # Estimate parameters from file size
            # Rough approximation: 1B params ~ 2GB for Q4, adjust for quantization
            if quant:
                quant_factor = self._get_quant_size_factor(quant)
            else:
                quant = self._extract_quant_from_filename(model_path)
                quant_factor = self._get_quant_size_factor(quant) if quant else 1.0
            
            # Estimate parameters and VRAM
            estimated_params = int((model_size_mb * 1_000_000_000) / (2_000 * quant_factor))
            vram_estimate = int(model_size_mb * 2.0)  # Conservative 2x model size
            
            return min(vram_estimate, 32 * 1024)  # Cap at 32GB
            
        except Exception as e:
            logger.warning(f"Could not estimate VRAM usage: {e}")
            return 4096  # Default 4GB estimate
    
    def _get_quant_size_factor(self, quant: str) -> float:
        """Get size factor for quantization type"""
        factors = {
            'FP16': 2.0, 'BF16': 2.0,
            'Q8_K_M': 1.0, 'Q8_0': 1.0,
            'Q6_K': 0.75,
            'Q5_K_M': 0.625, 'Q5_K_S': 0.625,
            'Q4_K_M': 0.5, 'Q4_K_S': 0.5, 'Q4_0': 0.5
        }
        return factors.get(quant, 1.0)
    
    def _extract_quant_from_filename(self, model_path: str) -> Optional[str]:
        """Extract quantization type from filename"""
        filename = Path(model_path).name.upper()
        
        # Common quantization patterns in GGUF filenames
        quant_patterns = [
            r'(Q[2-8]_[A-Z]+_[A-Z]+)',  # Q4_K_M, Q5_K_S, etc.
            r'(Q[2-8]_[A-Z]+)',         # Q4_K, Q5_K, etc.
            r'(Q[2-8]_[0-9])',          # Q8_0, Q4_0, etc.
            r'(Q[2-8]K)',               # Q4K, Q8K (alternative format)
            r'(FP16|BF16)',             # FP16, BF16
        ]
        
        for pattern in quant_patterns:
            match = re.search(pattern, filename)
            if match:
                return match.group(1)
        
        return None


# Global instance
_quant_manager = QuantizationManager()


def recommended_quants_for_backend(backend: str) -> List[str]:
    """Get recommended quantizations for a specific backend"""
    return _quant_manager.recommended_quants_for_backend(backend)


def pick_best_quant(model_quant: str, backend: str, vram_mb: int, model_params: Optional[int] = None) -> str:
    """Pick the best quantization for a model based on backend and available VRAM"""
    return _quant_manager.pick_best_quant(model_quant, backend, vram_mb, model_params)


def estimate_model_vram(model_path: str, quant: Optional[str] = None) -> int:
    """Estimate VRAM usage for a model"""
    return _quant_manager.estimate_model_vram(model_path, quant)


def extract_quant_from_filename(model_path: str) -> Optional[str]:
    """Extract quantization type from filename"""
    return _quant_manager._extract_quant_from_filename(model_path)
