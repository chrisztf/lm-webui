"""
Hardware backend modules for LLM-WebUI
Each backend implements the BackendRunner interface
"""
from typing import Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .base import BackendRunner

__all__ = ['get_backend_runner']


def get_backend_runner(backend: str) -> Optional['BackendRunner']:
    """
    Get backend runner for the specified backend
    
    Args:
        backend: One of 'cpu', 'cuda', 'rocm', 'metal'
        
    Returns:
        BackendRunner instance or None if backend not available
    """
    try:
        if backend == 'cpu':
            from .cpu import CPUBackend
            return CPUBackend()
        elif backend == 'cuda':
            from .cuda import CUDABackend
            return CUDABackend()
        elif backend == 'rocm':
            from .rocm import ROCmBackend
            return ROCmBackend()
        elif backend == 'metal':
            from .metal import MetalBackend
            return MetalBackend()
        else:
            return None
    except ImportError as e:
        # Backend not available due to missing dependencies
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Backend {backend} not available: {e}")
        return None
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error initializing backend {backend}: {e}")
        return None
