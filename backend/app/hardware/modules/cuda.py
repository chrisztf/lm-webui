"""
CUDA backend implementation for LLM-WebUI
Provides NVIDIA GPU acceleration with CUDA support
"""
import logging
import subprocess
from typing import Dict, Any, Optional
from pathlib import Path

from .base import BackendRunner

logger = logging.getLogger(__name__)

class CUDABackend(BackendRunner):
    """CUDA backend runner for NVIDIA GPU acceleration"""
    
    def __init__(self):
        super().__init__()
        self._llama_cli_path = self._find_llama_cli()
        self._available_vram = self._get_available_vram()
        
    @staticmethod
    def is_available() -> bool:
        """
        Check if CUDA backend is available
        
        Returns:
            True if CUDA is available, False otherwise
        """
        try:
            import torch
            if torch.cuda.is_available():
                device_count = torch.cuda.device_count()
                if device_count > 0:
                    logger.info(f"CUDA backend available with {device_count} GPU(s)")
                    return True
        except ImportError:
            logger.debug("PyTorch not available for CUDA detection")
        except Exception as e:
            logger.debug(f"CUDA availability check failed: {e}")
            
        return False
    
    def load_model(self, model_path: str, quant: str, **kwargs) -> Dict[str, Any]:
        """
        Load model for CUDA inference
        
        Args:
            model_path: Path to GGUF model file
            quant: Quantization type
            **kwargs: Additional parameters
            
        Returns:
            Model configuration dictionary
        """
        try:
            # Check VRAM compatibility
            vram_check = self.check_vram_compatibility(model_path, self._available_vram)
            if not vram_check["fits_vram"]:
                logger.warning(f"Model may not fit in VRAM: {vram_check['message']}")
                # We'll still try to load, but warn the user
                
            # Determine optimal GPU layers
            gpu_layers = self._calculate_optimal_gpu_layers(model_path)
            
            model_config = {
                "model_path": model_path,
                "quant": quant,
                "backend": "cuda",
                "use_gpu": True,
                "gpu_layers": gpu_layers,
                "available_vram": self._available_vram,
                "loaded": True
            }
            
            logger.info(f"CUDA backend configured for model: {Path(model_path).name} with {gpu_layers} GPU layers")
            return model_config
            
        except Exception as e:
            logger.error(f"Failed to configure CUDA backend for {model_path}: {e}")
            raise
    
    def run_inference(self, model_handle: Dict[str, Any], prompt: str, **kwargs) -> str:
        """
        Run inference using llama.cpp CLI with CUDA acceleration
        
        Args:
            model_handle: Model configuration from load_model
            prompt: Input prompt
            **kwargs: Additional inference parameters
            
        Returns:
            Generated text
        """
        if not self._llama_cli_path:
            raise RuntimeError("llama-cli not found. Please build llama.cpp with CUDA support.")
            
        try:
            # Build command for llama.cpp with CUDA
            cmd = [
                str(self._llama_cli_path),
                "-m", model_handle["model_path"],
                "-p", prompt,
                "--temp", str(kwargs.get("temperature", 0.7)),
                "--top-p", str(kwargs.get("top_p", 0.9)),
                "-n", str(kwargs.get("max_tokens", 512)),
                "-c", str(kwargs.get("context_size", 2048)),
                "-ngl", str(model_handle["gpu_layers"]),
                "--no-conversation",
                "--single-turn"
            ]
            
            # Run inference
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=kwargs.get("timeout", 60)
            )
            
            if result.returncode == 0 and result.stdout:
                # Parse response from llama-cli output
                response = self._parse_llama_output(result.stdout, prompt)
                return response
            else:
                error_msg = f"llama-cli failed with return code {result.returncode}"
                if result.stderr:
                    error_msg += f": {result.stderr[:200]}"
                raise RuntimeError(error_msg)
                
        except subprocess.TimeoutExpired:
            raise RuntimeError("CUDA inference timed out")
        except Exception as e:
            logger.error(f"CUDA inference failed: {e}")
            raise
    
    def unload_model(self, model_handle: Dict[str, Any]) -> None:
        """
        Unload model (CUDA backend doesn't need to do anything)
        
        Args:
            model_handle: Model configuration to unload
        """
        # CUDA backend doesn't keep models loaded in memory
        logger.info(f"CUDA backend unloaded model: {Path(model_handle['model_path']).name}")
    
    def _find_llama_cli(self) -> Optional[Path]:
        """Find llama-cli executable with CUDA support"""
        # Check common locations
        possible_paths = [
            Path(__file__).parent.parent.parent.parent / "llama.cpp" / "build" / "bin" / "llama-cli",
            Path(__file__).parent.parent.parent.parent / "llama.cpp" / "build" / "bin" / "llama",
            Path("/usr/local/bin/llama-cli"),
            Path("/usr/bin/llama-cli"),
        ]
        
        for path in possible_paths:
            if path.exists() and path.is_file():
                logger.info(f"Found llama-cli at: {path}")
                return path
                
        logger.warning("llama-cli not found. CUDA backend will not work without llama.cpp")
        return None
    
    def _get_available_vram(self) -> int:
        """Get available VRAM for CUDA devices"""
        try:
            import torch
            if torch.cuda.is_available():
                vram_mb = torch.cuda.get_device_properties(0).total_memory // (1024 * 1024)
                logger.info(f"CUDA VRAM available: {vram_mb}MB")
                return vram_mb
        except Exception as e:
            logger.warning(f"Could not determine CUDA VRAM: {e}")
            
        return 0  # Fallback
    
    def _calculate_optimal_gpu_layers(self, model_path: str) -> int:
        """
        Calculate optimal number of GPU layers for the model
        
        Args:
            model_path: Path to model file
            
        Returns:
            Number of GPU layers to use
        """
        try:
            # Estimate model size
            model_size_mb = Path(model_path).stat().st_size / (1024 * 1024)
            
            # Simple heuristic: use more layers for smaller models
            if model_size_mb < 2000:  # < 2GB
                return 32  # Most layers on GPU
            elif model_size_mb < 8000:  # < 8GB
                return 24  # Moderate layers
            elif model_size_mb < 16000:  # < 16GB
                return 16  # Fewer layers
            else:
                return 8   # Minimal layers for large models
                
        except Exception as e:
            logger.warning(f"Could not calculate optimal GPU layers: {e}")
            return 16  # Default fallback
    
    def _parse_llama_output(self, output: str, prompt: str) -> str:
        """Parse llama-cli output to extract the generated response"""
        lines = output.strip().split('\n')
        
        # Find the line that contains the generated response
        # Skip lines that contain the prompt or empty lines
        response_lines = []
        in_response = False
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Skip lines that are clearly part of the prompt or system output
            if line.startswith("Hello,") or line.startswith("build:") or line == prompt:
                continue
                
            # Once we find non-prompt content, start collecting
            if not in_response and line != prompt:
                in_response = True
                
            if in_response:
                response_lines.append(line)
        
        response = ' '.join(response_lines).strip()
        
        # If no response found, try to extract from the end
        if not response and lines:
            response = lines[-1].strip()
            
        return response if response else "No response generated"
