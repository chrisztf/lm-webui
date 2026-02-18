"""
CPU backend implementation for LLM-WebUI
Provides CPU-only inference with optimized quantization support
"""
import logging
import subprocess
import asyncio
from typing import Dict, Any, Optional
from pathlib import Path

from .base import BackendRunner

logger = logging.getLogger(__name__)

class CPUBackend(BackendRunner):
    """CPU backend runner for GGUF models"""
    
    def __init__(self):
        super().__init__()
        self._llama_cli_path = self._find_llama_cli()
        
    @staticmethod
    def is_available() -> bool:
        """
        CPU backend is always available as fallback
        
        Returns:
            True (CPU is always available)
        """
        return True
    
    def load_model(self, model_path: str, quant: str, **kwargs) -> Dict[str, Any]:
        """
        Load model for CPU inference
        
        Args:
            model_path: Path to GGUF model file
            quant: Quantization type
            **kwargs: Additional parameters
            
        Returns:
            Model configuration dictionary
        """
        try:
            # For CPU backend, we don't actually load the model into memory
            # We just store the configuration for inference
            model_config = {
                "model_path": model_path,
                "quant": quant,
                "backend": "cpu",
                "use_gpu": False,
                "threads": kwargs.get("threads", self._get_optimal_threads()),
                "loaded": True
            }
            
            logger.info(f"CPU backend configured for model: {Path(model_path).name}")
            return model_config
            
        except Exception as e:
            logger.error(f"Failed to configure CPU backend for {model_path}: {e}")
            raise
    
    def run_inference(self, model_handle: Dict[str, Any], prompt: str, **kwargs) -> str:
        """
        Run inference using llama.cpp CLI
        
        Args:
            model_handle: Model configuration from load_model
            prompt: Input prompt
            **kwargs: Additional inference parameters
            
        Returns:
            Generated text
        """
        if not self._llama_cli_path:
            raise RuntimeError("llama-cli not found. Please build llama.cpp first.")
            
        try:
            # Build command for llama.cpp
            cmd = [
                str(self._llama_cli_path),
                "-m", model_handle["model_path"],
                "-p", prompt,
                "--temp", str(kwargs.get("temperature", 0.7)),
                "--top-p", str(kwargs.get("top_p", 0.9)),
                "-n", str(kwargs.get("max_tokens", 512)),
                "-c", str(kwargs.get("context_size", 2048)),
                "--threads", str(model_handle["threads"]),
                "--no-conversation",
                "--single-turn"
            ]
            
            # Add GPU layers (0 for CPU-only)
            cmd.extend(["-ngl", "0"])
            
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
            raise RuntimeError("CPU inference timed out")
        except Exception as e:
            logger.error(f"CPU inference failed: {e}")
            raise
    
    def unload_model(self, model_handle: Dict[str, Any]) -> None:
        """
        Unload model (CPU backend doesn't need to do anything)
        
        Args:
            model_handle: Model configuration to unload
        """
        # CPU backend doesn't keep models loaded in memory
        logger.info(f"CPU backend unloaded model: {Path(model_handle['model_path']).name}")
    
    def _find_llama_cli(self) -> Optional[Path]:
        """Find llama-cli executable"""
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
                
        logger.warning("llama-cli not found. CPU backend will not work without llama.cpp")
        return None
    
    def _get_optimal_threads(self) -> int:
        """Get optimal number of threads for CPU inference"""
        import os
        try:
            # Use all available cores, but leave 1-2 for system
            cpu_count = os.cpu_count() or 4
            return max(1, cpu_count - 2)
        except:
            return 4  # Default fallback
    
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
