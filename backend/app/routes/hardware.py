"""
Hardware Routes

This module provides routes for hardware detection and management.
"""

from fastapi import APIRouter
import psutil
import platform

router = APIRouter(prefix="/api/hardware")

@router.get("/info")
async def hardware_info():
    """Get hardware information"""
    # Get CPU information
    cpu_count = psutil.cpu_count()
    cpu_freq = psutil.cpu_freq()
    
    # Get memory information
    memory = psutil.virtual_memory()
    
    # Get disk information
    disk = psutil.disk_usage('/')
    
    # Get network information
    net_io = psutil.net_io_counters()
    
    return {
        "cpu": {
            "cores": cpu_count,
            "threads": psutil.cpu_count(logical=True),
            "frequency_mhz": cpu_freq.current if cpu_freq else None,
            "usage_percent": psutil.cpu_percent(interval=1)
        },
        "memory": {
            "total_gb": round(memory.total / (1024**3), 2),
            "available_gb": round(memory.available / (1024**3), 2),
            "used_gb": round(memory.used / (1024**3), 2),
            "usage_percent": memory.percent
        },
        "disk": {
            "total_gb": round(disk.total / (1024**3), 2),
            "free_gb": round(disk.free / (1024**3), 2),
            "used_gb": round(disk.used / (1024**3), 2),
            "usage_percent": disk.percent
        },
        "network": {
            "bytes_sent": net_io.bytes_sent,
            "bytes_recv": net_io.bytes_recv,
            "packets_sent": net_io.packets_sent,
            "packets_recv": net_io.packets_recv
        },
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor()
        }
    }

@router.get("/gpu")
async def gpu_info():
    """Get GPU information (placeholder)"""
    # This would typically use libraries like pynvml for NVIDIA GPUs
    # or other platform-specific methods
    
    return {
        "gpus": [
            {
                "name": "Apple M1/M2 GPU",
                "memory_total_mb": 8192,
                "memory_used_mb": 1024,
                "driver_version": "Metal",
                "cuda_available": False
            }
        ]
    }

@router.get("/performance")
async def performance_metrics():
    """Get real-time performance metrics"""
    return {
        "cpu_percent": psutil.cpu_percent(interval=1),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_io": {
            "read_bytes": psutil.disk_io_counters().read_bytes,
            "write_bytes": psutil.disk_io_counters().write_bytes
        },
        "network_io": {
            "bytes_sent": psutil.net_io_counters().bytes_sent,
            "bytes_recv": psutil.net_io_counters().bytes_recv
        }
    }
