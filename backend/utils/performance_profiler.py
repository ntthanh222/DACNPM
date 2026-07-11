"""
Performance profiling utilities for CyberSec Assistant Platform.

Provides comprehensive performance monitoring and profiling capabilities
including execution time tracking, memory profiling, and database query monitoring.
"""

import time
import functools
import logging
from typing import Callable, Any, Dict, List, Optional
from contextlib import contextmanager
from datetime import datetime, timedelta
import cProfile
import pstats
import io
import memory_profiler
from pathlib import Path

logger = logging.getLogger(__name__)


class PerformanceMetrics:
    """Container for performance metrics."""

    def __init__(self):
        self.execution_time: float = 0.0
        self.memory_used: float = 0.0
        self.db_queries: int = 0
        self.cache_hits: int = 0
        self.cache_misses: int = 0
        self.api_calls: int = 0
        self.error_count: int = 0
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "execution_time": self.execution_time,
            "memory_used_mb": self.memory_used,
            "db_queries": self.db_queries,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "cache_hit_rate": self._calculate_hit_rate(),
            "api_calls": self.api_calls,
            "error_count": self.error_count,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None
        }

    def _calculate_hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.cache_hits + self.cache_misses
        if total == 0:
            return 0.0
        return (self.cache_hits / total) * 100


class PerformanceProfiler:
    """Main performance profiling class."""

    def __init__(self):
        self.metrics = PerformanceMetrics()
        self._query_count = 0
        self._profile_stack: List[Dict[str, Any]] = []

    @contextmanager
    def profile_operation(self, operation_name: str = "operation"):
        """Context manager for profiling operations."""
        start_time = time.time()
        start_memory = self._get_memory_usage()

        operation_data = {
            "name": operation_name,
            "start_time": datetime.now(),
            "metrics": PerformanceMetrics()
        }
        self._profile_stack.append(operation_data)

        try:
            yield operation_data["metrics"]

        finally:
            end_time = time.time()
            end_memory = self._get_memory_usage()

            operation_data["metrics"].execution_time = end_time - start_time
            operation_data["metrics"].memory_used = end_memory - start_memory
            operation_data["metrics"].end_time = datetime.now()

            self._profile_stack.pop()

            if not self._profile_stack:
                # This is the top-level operation
                self.metrics = operation_data["metrics"]

    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        try:
            import psutil
            import os
            process = psutil.Process(os.getpid())
            return process.memory_info().rss / (1024 * 1024)  # Convert to MB
        except ImportError:
            return 0.0

    def get_metrics(self) -> PerformanceMetrics:
        """Get current performance metrics."""
        return self.metrics

    def reset(self):
        """Reset profiling metrics."""
        self.metrics = PerformanceMetrics()
        self._query_count = 0


class DatabaseQueryProfiler:
    """Database query profiling wrapper."""

    def __init__(self):
        self.query_count = 0
        self.slow_queries: List[Dict[str, Any]] = []
        self.slow_threshold = 0.1  # 100ms

    def record_query(self, query: str, execution_time: float):
        """Record a database query."""
        self.query_count += 1

        if execution_time > self.slow_threshold:
            self.slow_queries.append({
                "query": query[:200],  # Truncate long queries
                "execution_time": execution_time,
                "timestamp": datetime.now()
            })

    def get_stats(self) -> Dict[str, Any]:
        """Get query statistics."""
        return {
            "total_queries": self.query_count,
            "slow_queries": len(self.slow_queries),
            "slow_query_details": self.slow_queries[-10:]  # Last 10 slow queries
        }


def profile_function(func: Callable) -> Callable:
    """Decorator to profile function execution."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        profiler = PerformanceProfiler()

        with profiler.profile_operation(func.__name__):
            result = func(*args, **kwargs)

        # Log performance data
        metrics = profiler.get_metrics()
        logger.info(
            f"Function '{func.__name__}' executed in {metrics.execution_time:.4f}s "
            f"using {metrics.memory_used:.2f}MB"
        )

        return result

    return wrapper


def profile_async_function(func: Callable) -> Callable:
    """Decorator to profile async function execution."""

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        profiler = PerformanceProfiler()

        with profiler.profile_operation(func.__name__):
            result = await func(*args, **kwargs)

        # Log performance data
        metrics = profiler.get_metrics()
        logger.info(
            f"Async function '{func.__name__}' executed in {metrics.execution_time:.4f}s "
            f"using {metrics.memory_used:.2f}MB"
        )

        return result

    return wrapper


def detailed_profile(func: Callable) -> Callable:
    """Decorator for detailed profiling with cProfile."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        profiler = cProfile.Profile()
        profiler.enable()

        try:
            result = func(*args, **kwargs)
        finally:
            profiler.disable()

            # Print profiling statistics
            s = io.StringIO()
            stats = pstats.Stats(profiler, stream=s)
            stats.strip_dirs()
            stats.sort_stats('cumulative')
            stats.print_stats(20)  # Top 20 functions

            logger.info(f"Detailed profile for '{func.__name__}':\n{s.getvalue()}")

        return result

    return wrapper


class PerformanceMonitor:
    """Global performance monitoring singleton."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.profiler = PerformanceProfiler()
            cls._instance.db_profiler = DatabaseQueryProfiler()
            cls._instance.operation_history: List[Dict[str, Any]] = []
        return cls._instance

    def record_operation(self, operation_name: str, metrics: PerformanceMetrics):
        """Record operation performance metrics."""
        self.operation_history.append({
            "name": operation_name,
            "metrics": metrics.to_dict(),
            "timestamp": datetime.now()
        })

        # Keep only last 1000 operations
        if len(self.operation_history) > 1000:
            self.operation_history.pop(0)

    def get_slow_operations(self, threshold_seconds: float = 1.0) -> List[Dict[str, Any]]:
        """Get operations that exceeded threshold."""
        return [
            op for op in self.operation_history
            if op["metrics"]["execution_time"] > threshold_seconds
        ]

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get overall performance summary."""
        if not self.operation_history:
            return {"status": "no_data"}

        execution_times = [op["metrics"]["execution_time"] for op in self.operation_history]
        memory_usage = [op["metrics"]["memory_used_mb"] for op in self.operation_history]

        return {
            "total_operations": len(self.operation_history),
            "avg_execution_time": sum(execution_times) / len(execution_times),
            "max_execution_time": max(execution_times),
            "min_execution_time": min(execution_times),
            "avg_memory_usage": sum(memory_usage) / len(memory_usage),
            "max_memory_usage": max(memory_usage),
            "db_query_stats": self.db_profiler.get_stats(),
            "slow_operations_count": len(self.get_slow_operations())
        }


# Global instance
performance_monitor = PerformanceMonitor()