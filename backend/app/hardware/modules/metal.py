"""
Metal backend implementation for LLM-WebUI
Provides Apple Silicon GPU acceleration with Metal support
Consolidated Apple Silicon functions - single source of truth
"""
import logging
import subprocess
import platform
import psutil
import os
from typing import Dict, Any, Optional
from pathlib import Path

from .base import BackendRunner

logger = logging.getLogger(__name__)


class AppleSiliconSupport:
    """Apple Silicon optimization utilities - consolidated from services/apple_silicon.py"""
    
    def __init__(self):
        self.is_apple_silicon = self._detect_apple_silicon()
        self.metal_support = self._check_metal_support()
        self.metal_vram_limit = self._get_metal_vram_limit()
        
    def _detect_apple_silicon(self) -> bool:
        """Detect if running on Apple Silicon hardware"""
        try:
            # Check system architecture
            result = subprocess.run(['uname', '-m'], capture_output=True, text=True)
            arch = result.stdout.strip().lower()
            
            # Check for Apple Silicon architecture
            if arch in ['arm64', 'aarch64']:
                # Check if we're on macOS (Darwin kernel)
                os_result = subprocess.run(['uname', '-s'], capture_output=True, text=True)
                os_name = os_result.stdout.strip().lower()
                
                # If we're on arm64 macOS (Darwin), it's Apple Silicon
                if os_name == 'darwin' and arch == 'arm64':
                    return True
                
                # Additional check for Apple-specific hardware
                try:
                    result = subprocess.run(['sysctl', '-n', 'hw.machine'], 
                                          capture_output=True, text=True)
                    machine = result.stdout.strip().lower()
                    return any(keyword in machine for keyword in ['apple', 'm1', 'm2', 'm3', 'mac'])
                except:
                    # If sysctl fails but we're on arm64, assume Apple Silicon
                    return True
            return False
        except Exception as e:
            logger.warning(f"Could not detect Apple Silicon: {e}")
            return False
    
    def _check_metal_support(self) -> bool:
        """Check if Metal framework is available"""
        if not self.is_apple_silicon:
            return False
            
        try:
            # Check if we're on macOS (Metal is only available on macOS)
            result = subprocess.run(['uname', '-s'], capture_output=True, text=True)
            os_name = result.stdout.strip().lower()
            
            if os_name != 'darwin':  # Darwin is macOS kernel
                return False
                
            # Check if Metal framework exists
            metal_framework_path = '/System/Library/Frameworks/Metal.framework'
            if os.path.exists(metal_framework_path):
                return True
                
            # Assume Metal is available on Apple Silicon macOS
            return True
                
        except Exception as e:
            logger.warning(f"Could not check Metal support: {e}")
            # Assume Metal is available on Apple Silicon macOS
            return True
    
    def _get_metal_vram_limit(self) -> float:
        """Get available Metal VRAM in GB"""
        try:
            if not self.is_apple_silicon:
                return 0.0
                
            # Get system RAM and estimate VRAM allocation
            total_ram_gb = psutil.virtual_memory().total / (1024**3)
            
            # Apple Silicon typically allocates up to 50% of RAM to GPU
            # Conservative estimate for stability
            if total_ram_gb >= 64:
                return min(32.0, total_ram_gb * 0.4)  # Up to 32GB for high-end systems
            elif total_ram_gb >= 32:
                return min(16.0, total_ram_gb * 0.5)  # Up to 16GB for mid-range
            else:
                return min(8.0, total_ram_gb * 0.6)   # Up to 8GB for lower-end
                
        except Exception as e:
            logger.warning(f"Could not determine Metal VRAM limit: {e}")
            return 8.0  # Default conservative estimate
    
    def get_optimized_config(self, model_path: str) -> Dict:
        """
        Get optimized configuration for Apple Silicon
        
        Args:
            model_path: Path to GGUF model file
            
        Returns:
            Dictionary with optimized configuration
        """
        try:
            # Estimate model VRAM usage
            model_vram_usage = self._estimate_model_vram_usage(model_path)
            
            # Check if model fits in available VRAM
            use_gpu = self.is_apple_silicon and self.metal_support and (model_vram_usage <= self.metal_vram_limit)
            fallback_reason = ""
            
            if not use_gpu and self.is_apple_silicon:
                if model_vram_usage > self.metal_vram_limit:
                    fallback_reason = f"⚠️ Model too large for GPU ({self.metal_vram_limit:.1f}GB available). Running in CPU fallback — slower performance."
                elif not self.metal_support:
                    fallback_reason = "⚠️ Metal support not available. Running in CPU fallback."
            
            return {
                "model_path": model_path,
                "use_gpu": use_gpu,
                "fallback_reason": fallback_reason,
                "metal_vram_limit_gb": self.metal_vram_limit,
                "estimated_vram_usage_gb": model_vram_usage,
                "apple_silicon_detected": self.is_apple_silicon,
                "metal_support": self.metal_support
            }
            
        except Exception as e:
            logger.error(f"Error getting optimized config: {e}")
            # Fallback to safe defaults
            return {
                "model_path": model_path,
                "use_gpu": False,
                "fallback_reason": f"Error: {str(e)}",
                "metal_vram_limit_gb": 0.0,
                "estimated_vram_usage_gb": 0.0,
                "apple_silicon_detected": self.is_apple_silicon,
                "metal_support": self.metal_support
            }
    
    def _estimate_model_vram_usage(self, model_path: str) -> float:
        """Estimate VRAM usage for a model in GB"""
        try:
            # Get model file size
            model_size_bytes = Path(model_path).stat().st_size
            
            # Rough estimation: VRAM usage is typically 1.5-2x model size
            vram_usage_gb = (model_size_bytes * 2) / (1024**3)
            
            return vram_usage_gb
            
        except Exception as e:
            logger.warning(f"Could not estimate VRAM usage: {e}")
            return 0.0


# Global instance
apple_silicon_support = AppleSiliconSupport()


def get_apple_silicon_config(model_path: str) -> Dict:
    """Convenience function to get Apple Silicon optimized configuration"""
    return apple_silicon_support.get_optimized_config(model_path)


def is_apple_silicon() -> bool:
    """Check if running on Apple Silicon"""
    return apple_silicon_support.is_apple_silicon


def has_metal_support() -> bool:
    """Check if Metal framework is available"""
    return apple_silicon_support.metal_support


def get_metal_vram_limit() -> float:
    """Get available Metal VRAM in GB"""
    return apple_silicon_support.metal_vram_limit

class MetalBackend(BackendRunner):
    """Metal backend runner for Apple Silicon GPU acceleration"""
    
    def __init__(self):
        super().__init__()
        self._llama_cli_path = self._find_llama_cli()
        self._available_vram = self._get_available_vram()
        
    @staticmethod
    def is_available() -> bool:
        """
        Check if Metal backend is available
        
        Returns:
            True if Metal is available, False otherwise
        """
        # Check if we're on macOS with Apple Silicon
        if platform.system() != "Darwin":
            return False
            
        # Check architecture
        arch = platform.machine()
        if arch not in ['arm64', 'aarch64']:
            return False
            
        # Check for Apple Silicon specific hardware
        try:
            result = subprocess.run(['sysctl', '-n', 'hw.model'], capture_output=True, text=True)
            model = result.stdout.strip().lower()
            if any(keyword in model for keyword in ['mac', 'm1', 'm2', 'm3', 'm4']):
                logger.info(f"Metal backend available on Apple {model.upper()}")
                return True
        except:
            # If sysctl fails but we're on arm64 macOS, assume Apple Silicon
            logger.info("Metal backend available on Apple Silicon (arm64 macOS)")
            return True
            
        return False
    
    def load_model(self, model_path: str, quant: str, **kwargs) -> Dict[str, Any]:
        """
        Load model for Metal inference
        
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
                
            # Determine optimal GPU layers for Metal
            gpu_layers = self._calculate_optimal_gpu_layers(model_path)
            
            model_config = {
                "model_path": model_path,
                "quant": quant,
                "backend": "metal",
                "use_gpu": True,
                "gpu_layers": gpu_layers,
                "available_vram": self._available_vram,
                "loaded": True
            }
            
            logger.info(f"Metal backend configured for model: {Path(model_path).name} with {gpu_layers} GPU layers")
            return model_config
            
        except Exception as e:
            logger.error(f"Failed to configure Metal backend for {model_path}: {e}")
            raise
    
    def run_inference(self, model_handle: Dict[str, Any], prompt: str, **kwargs) -> str:
        """
        Run inference using llama.cpp CLI with Metal acceleration
        
        Args:
            model_handle: Model configuration from load_model
            prompt: Input prompt
            **kwargs: Additional inference parameters
            
        Returns:
            Generated text
        """
        if not self._llama_cli_path:
            raise RuntimeError("llama-cli not found. Please build llama.cpp with Metal support.")
            
        try:
            # Build command for llama.cpp with Metal
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
            raise RuntimeError("Metal inference timed out")
        except Exception as e:
            logger.error(f"Metal inference failed: {e}")
            raise
    
    def unload_model(self, model_handle: Dict[str, Any]) -> None:
        """
        Unload model (Metal backend doesn't need to do anything)
        
        Args:
            model_handle: Model configuration to unload
        """
        # Metal backend doesn't keep models loaded in memory
        logger.info(f"Metal backend unloaded model: {Path(model_handle['model_path']).name}")
    
    def _find_llama_cli(self) -> Optional[Path]:
        """Find llama-cli executable with Metal support"""
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
                
        logger.warning("llama-cli not found. Metal backend will not work without llama.cpp")
        return None
    
    def _get_available_vram(self) -> int:
        """Get available VRAM for Metal devices"""
        try:
            import psutil
            # Estimate Metal VRAM (shared with system RAM)
            total_ram_gb = psutil.virtual_memory().total / (1024**3)
            metal_vram_gb = self._estimate_metal_vram(total_ram_gb)
            vram_mb = int(metal_vram_gb * 1024)
            
            logger.info(f"Metal VRAM estimated: {vram_mb}MB (from {total_ram_gb:.1f}GB system RAM)")
            return vram_mb
            
        except Exception as e:
            logger.warning(f"Could not determine Metal VRAM: {e}")
            return 8192  # Default 8GB fallback
    
    def _estimate_metal_vram(self, total_ram_gb: float) -> float:
        """Estimate available Metal VRAM based on system RAM"""
        # Conservative estimates for shared memory systems
        if total_ram_gb >= 64:
            return min(32.0, total_ram_gb * 0.4)  # Up to 32GB for high-end
        elif total_ram_gb >= 32:
            return min(16.0, total_ram_gb * 0.5)  # Up to 16GB for mid-range
        else:
            return min(8.0, total_ram_gb * 0.6)   # Up to 8GB for lower-end
    
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
            
            # Metal-specific heuristic: Apple Silicon has unified memory
            # so we can be more aggressive with GPU layers
            if model_size_mb < 4000:  # < 4GB
                return 99  # Most layers on GPU (Metal can handle it)
            elif model_size_mb < 8000:  # < 8GB
                return 64  # Many layers
            elif model_size_mb < 16000:  # < 16GB
                return 32  # Moderate layers
            else:
                return 16  # Conservative for large models
                
        except Exception as e:
            logger.warning(f"Could not calculate optimal GPU layers: {e}")
            return 32  # Default fallback for Metal
    
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
