"""
Performance Monitoring and Request Batching

This module provides performance monitoring and request batching capabilities
for the ModelRegistry and other services.
"""

import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import asyncio

class PerformanceMonitor:
    """
    Monitors performance metrics for model fetching and other operations.
    
    Tracks:
    - Request latencies
    - Cache hit rates
    - Error rates
    - Provider performance
    """
    
    def __init__(self):
        self._metrics: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self._batch_operations: Dict[str, List[Any]] = defaultdict(list)
        self._batch_lock = asyncio.Lock()
        
        # Performance thresholds (in seconds)
        self._thresholds = {
            "fast": 1.0,
            "medium": 3.0,
            "slow": 10.0
        }
    
    def record_metric(self, operation: str, duration: float, success: bool = True, 
                     provider: Optional[str] = None, details: Optional[Dict] = None):
        """Record a performance metric"""
        metric = {
            "timestamp": datetime.utcnow().isoformat(),
            "operation": operation,
            "duration": duration,
            "success": success,
            "provider": provider,
            "details": details or {}
        }
        
        self._metrics[operation].append(metric)
        
        # Keep only last 1000 metrics per operation
        if len(self._metrics[operation]) > 1000:
            self._metrics[operation] = self._metrics[operation][-1000:]
    
    async def batch_operation(self, batch_key: str, operation, *args, **kwargs):
        """
        Batch similar operations to reduce API calls.
        
        Example: Multiple model fetches for the same provider can be batched.
        """
        async with self._batch_lock:
            # Check if there's already a batch for this key
            if batch_key in self._batch_operations:
                # Add to existing batch
                self._batch_operations[batch_key].append((args, kwargs))
                return None
            
            # Create new batch
            self._batch_operations[batch_key] = [(args, kwargs)]
            
            # Schedule batch execution
            asyncio.create_task(self._execute_batch(batch_key, operation))
    
    async def _execute_batch(self, batch_key: str, operation):
        """Execute a batch of operations"""
        await asyncio.sleep(0.1)  # Small delay to collect more operations
        
        async with self._batch_lock:
            if batch_key not in self._batch_operations:
                return
            
            batch_items = self._batch_operations.pop(batch_key)
            
            if not batch_items:
                return
            
            # Execute the batch
            start_time = time.time()
            try:
                # For now, execute sequentially
                # In a real implementation, this could be optimized
                results = []
                for args, kwargs in batch_items:
                    result = await operation(*args, **kwargs)
                    results.append(result)
                
                duration = time.time() - start_time
                self.record_metric(
                    f"batch_{batch_key}",
                    duration,
                    success=True,
                    details={"batch_size": len(batch_items)}
                )
                
                return results
            except Exception as e:
                duration = time.time() - start_time
                self.record_metric(
                    f"batch_{batch_key}",
                    duration,
                    success=False,
                    details={"error": str(e), "batch_size": len(batch_items)}
                )
                raise
    
    def get_metrics(self, operation: Optional[str] = None, 
                   time_window: Optional[timedelta] = None) -> Dict[str, Any]:
        """Get performance metrics"""
        if operation:
            metrics = self._metrics.get(operation, [])
        else:
            metrics = []
            for op_metrics in self._metrics.values():
                metrics.extend(op_metrics)
        
        # Filter by time window if specified
        if time_window:
            cutoff = datetime.utcnow() - time_window
            metrics = [m for m in metrics if datetime.fromisoformat(m["timestamp"]) > cutoff]
        
        if not metrics:
            return {"count": 0, "avg_duration": 0, "success_rate": 0}
        
        # Calculate statistics
        total_duration = sum(m["duration"] for m in metrics)
        success_count = sum(1 for m in metrics if m["success"])
        
        return {
            "count": len(metrics),
            "avg_duration": total_duration / len(metrics),
            "success_rate": success_count / len(metrics) * 100,
            "min_duration": min(m["duration"] for m in metrics),
            "max_duration": max(m["duration"] for m in metrics),
            "recent_metrics": metrics[-10:]  # Last 10 metrics
        }
    
    def get_provider_performance(self, provider: str, 
                                time_window: Optional[timedelta] = None) -> Dict[str, Any]:
        """Get performance metrics for a specific provider"""
        provider_metrics = []
        for op_metrics in self._metrics.values():
            for metric in op_metrics:
                if metric.get("provider") == provider:
                    provider_metrics.append(metric)
        
        # Filter by time window if specified
        if time_window:
            cutoff = datetime.utcnow() - time_window
            provider_metrics = [m for m in provider_metrics 
                              if datetime.fromisoformat(m["timestamp"]) > cutoff]
        
        if not provider_metrics:
            return {
                "provider": provider, 
                "count": 0, 
                "avg_duration": 0, 
                "success_rate": 0,
                "performance": "unknown"
            }
        
        # Calculate statistics
        total_duration = sum(m["duration"] for m in provider_metrics)
        success_count = sum(1 for m in provider_metrics if m["success"])
        avg_duration = total_duration / len(provider_metrics)
        
        return {
            "provider": provider,
            "count": len(provider_metrics),
            "avg_duration": avg_duration,
            "success_rate": success_count / len(provider_metrics) * 100,
            "performance": self._get_performance_rating(avg_duration)
        }
    
    def _get_performance_rating(self, avg_duration: float) -> str:
        """Get performance rating based on average duration"""
        if avg_duration <= self._thresholds["fast"]:
            return "fast"
        elif avg_duration <= self._thresholds["medium"]:
            return "medium"
        else:
            return "slow"
    
    def clear_metrics(self):
        """Clear all metrics"""
        self._metrics.clear()


# Global PerformanceMonitor instance
_performance_monitor = None

def get_performance_monitor() -> PerformanceMonitor:
    """Get or create the global PerformanceMonitor instance"""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor
