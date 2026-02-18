"""
Simplified model optimization utilities for llama.cpp integration
Focuses on quantization support and process management, delegates Apple Silicon to hardware/backends/metal.py
"""
import re
import logging
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from hardware.modules.metal import get_apple_silicon_config, apple_silicon_support

logger = logging.getLogger(__name__)

class ModelOptimizer:
    """Simplified model optimization utilities"""
    
    # Enable all Q4, Q5, Q6, Q8 variants as requested
    DEFAULT_SUPPORTED_QUANTS = {
        # Q4 variants
        'Q4': True, 'Q4_K': True, 'Q4_K_M': True, 'Q4_K_S': True, 'Q4_K_L': True, 'Q4_0': True,
        # Q5 variants  
        'Q5': True, 'Q5_K': True, 'Q5_K_M': True, 'Q5_K_S': True,
        # Q6 variants
        'Q6': True, 'Q6_K': True,
        # Q8 variants
        'Q8': True, 'Q8_K': True, 'Q8_K_M': True, 'Q8_0': True,
        # FP16/BF16
        'FP16': True, 'BF16': True
    }
    
    def __init__(self):
        # Initialize Apple Silicon support
        self.apple_silicon = apple_silicon_support
    
    def check_quantization_support(self, model_path: str) -> Dict:
        """
        Simple quantization support check - all Q4, Q5, Q6, Q8 variants are supported
        
        Args:
            model_path: Path to GGUF model file
            
        Returns:
            Dictionary with quantization support information
        """
        try:
            # Extract quantization from filename
            quant = self._extract_quant_from_filename(model_path)
            
            if not quant:
                return {
                    "supported": True,
                    "quant": "unknown",
                    "message": "Could not determine quantization type",
                    "fallback": False,
                    "warnings": []
                }
            
            # All Q4, Q5, Q6, Q8 variants are supported
            is_supported = self.DEFAULT_SUPPORTED_QUANTS.get(quant, True)
            
            return {
                "supported": is_supported,
                "quant": quant,
                "message": f"Quantization {quant} analysis complete",
                "fallback": False,
                "warnings": [],
                "recommended": list(self.DEFAULT_SUPPORTED_QUANTS.keys())
            }
            
        except Exception as e:
            logger.error(f"Error checking quantization support: {e}")
            return {
                "supported": True,  # Default to supported on error
                "quant": "unknown",
                "message": f"Error checking support: {str(e)}",
                "fallback": False,
                "warnings": []
            }
    
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
                quant = match.group(1)
                # Normalize the quantization format
                if '_K_' in quant:
                    # Handle Q4_K_M format
                    return quant
                elif '_K' in quant and '_' not in quant.split('_K')[1]:
                    # Handle Q4_K format
                    return quant
                else:
                    return quant
        
        return None
    
    def get_optimized_runtime_config(self, model_path: str) -> Dict:
        """
        Get optimized runtime configuration for a model
        Uses Apple Silicon optimization from apple_silicon.py
        
        Args:
            model_path: Path to GGUF model file
            
        Returns:
            Dictionary with runtime configuration
        """
        try:
            # Get Apple Silicon optimized configuration
            apple_config = get_apple_silicon_config(model_path)
            
            # Get quantization info
            quant_info = self.check_quantization_support(model_path)
            
            # Combine configurations
            config = {
                "model_path": model_path,
                "use_gpu": apple_config["use_gpu"],
                "fallback_reason": apple_config["fallback_reason"],
                "metal_vram_limit_gb": apple_config["metal_vram_limit_gb"],
                "estimated_vram_usage_gb": apple_config["estimated_vram_usage_gb"],
                "quantization_info": quant_info,
                "apple_silicon_detected": apple_config["apple_silicon_detected"],
                "metal_support": apple_config["metal_support"]
            }
            
            # Log warnings if any
            if config["fallback_reason"]:
                logger.warning(config["fallback_reason"])
            
            return config
            
        except Exception as e:
            logger.error(f"Error getting optimized config: {e}")
            # Fallback to safe defaults
            return {
                "model_path": model_path,
                "use_gpu": False,
                "fallback_reason": f"Error: {str(e)}",
                "metal_vram_limit_gb": 0.0,
                "estimated_vram_usage_gb": 0.0,
                "quantization_info": {
                    "supported": True,
                    "quant": "unknown",
                    "message": f"Error: {str(e)}",
                    "fallback": False,
                    "warnings": []
                }
            }


class ProcessManager:
    """Enhanced process management with graceful fallback and timeout handling"""
    
    def __init__(self, timeout_seconds: int = 30):
        self.timeout_seconds = timeout_seconds
        self.running_processes = {}
        
    async def run_with_timeout(self, cmd: List[str], session_id: str, model_config: Dict) -> Dict:
        """
        Run a command with timeout and graceful fallback handling
        
        Args:
            cmd: Command to execute
            session_id: Unique session identifier
            model_config: Model configuration from ModelOptimizer
            
        Returns:
            Dictionary with process result
        """
        try:
            # Start the process
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            self.running_processes[session_id] = process
            
            try:
                # Wait for process completion with timeout
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.timeout_seconds
                )
                
                # Process completed successfully
                return {
                    "success": True,
                    "stdout": stdout.decode() if stdout else "",
                    "stderr": stderr.decode() if stderr else "",
                    "returncode": process.returncode
                }
                
            except asyncio.TimeoutError:
                # Process timed out - kill it gracefully
                logger.warning(f"Process {session_id} timed out after {self.timeout_seconds}s")
                process.terminate()
                
                try:
                    # Give it a moment to terminate gracefully
                    await asyncio.wait_for(process.wait(), timeout=5)
                except asyncio.TimeoutError:
                    # Force kill if still running
                    process.kill()
                    await process.wait()
                
                return {
                    "success": False,
                    "error": f"Process timed out after {self.timeout_seconds} seconds",
                    "returncode": process.returncode
                }
                
        except Exception as e:
            logger.error(f"Error running process {session_id}: {e}")
            return {
                "success": False,
                "error": f"Process execution failed: {str(e)}"
            }
        finally:
            # Clean up process tracking
            self.running_processes.pop(session_id, None)
    
    def kill_process(self, session_id: str) -> bool:
        """Kill a specific process by session_id"""
        process = self.running_processes.get(session_id)
        if process:
            try:
                process.terminate()
                # Don't wait for termination in this method
                return True
            except Exception as e:
                logger.error(f"Error killing process {session_id}: {e}")
                return False
        return False
    
    def get_running_processes(self) -> List[str]:
        """Get list of currently running session IDs"""
        return list(self.running_processes.keys())


# Global instances for easy access
model_optimizer = ModelOptimizer()
process_manager = ProcessManager()


# Convenience functions
def optimize_model_config(model_path: str) -> Dict:
    """Convenience function to get optimized model configuration"""
    return model_optimizer.get_optimized_runtime_config(model_path)


def check_model_compatibility(model_path: str) -> Dict:
    """Convenience function to check model compatibility"""
    return model_optimizer.check_quantization_support(model_path)


async def run_llama_process(cmd: List[str], session_id: str, model_path: str) -> Dict:
    """
    Run llama.cpp process with optimized configuration
    
    Args:
        cmd: Command to execute
        session_id: Unique session identifier
        model_path: Path to model file
        
    Returns:
        Dictionary with process result
    """
    # Get optimized configuration
    config = optimize_model_config(model_path)
    
    # Run the process with timeout management
    return await process_manager.run_with_timeout(cmd, session_id, config)
