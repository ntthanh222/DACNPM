import time
import logging
from typing import Callable, Dict, Any, List
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from datetime import datetime

from backend.utils.performance_profiler import PerformanceMonitor, performance_monitor

logger = logging.getLogger(__name__)


class PerformanceMiddleware(BaseHTTPMiddleware):
    """Middleware to track performance metrics for all requests."""

    def __init__(self, app: ASGIApp, enable_detailed_logging: bool = False):
        super().__init__(app)
        self.enable_detailed_logging = enable_detailed_logging
        self.request_stats: Dict[str, Dict[str, Any]] = {}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and track performance metrics."""
        start_time = time.time()
        start_memory = self._get_memory_usage()

        # Generate request ID
        request_id = f"{request.method}:{request.url.path}"

        try:
            # Process request
            response = await call_next(request)

            # Calculate metrics
            end_time = time.time()
            end_memory = self._get_memory_usage()

            execution_time = end_time - start_time
            memory_used = end_memory - start_memory

            # Store request statistics
            self._update_request_stats(request_id, execution_time, response.status_code)

            # Log performance data
            self._log_performance(
                request,
                execution_time,
                memory_used,
                response.status_code
            )

            # Add performance headers
            response.headers["X-Response-Time"] = f"{execution_time:.4f}"
            response.headers["X-Memory-Used"] = f"{memory_used:.2f}"

            # Record in global monitor
            performance_monitor.record_operation(request_id, {
                "execution_time": execution_time,
                "memory_used": memory_used,
                "status_code": response.status_code,
                "start_time": datetime.fromtimestamp(start_time),
                "end_time": datetime.fromtimestamp(end_time)
            })

            return response

        except Exception as e:
            # Log error performance
            execution_time = time.time() - start_time
            logger.error(
                f"Request {request_id} failed after {execution_time:.4f}s: {str(e)}"
            )
            raise

    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        try:
            import psutil
            import os
            process = psutil.Process(os.getpid())
            return process.memory_info().rss / (1024 * 1024)  # Convert to MB
        except Exception:
            return 0.0

    def _update_request_stats(self, request_id: str, execution_time: float, status_code: int):
        """Update request statistics."""
        if request_id not in self.request_stats:
            self.request_stats[request_id] = {
                "count": 0,
                "total_time": 0.0,
                "success_count": 0,
                "error_count": 0,
                "min_time": float('inf'),
                "max_time": 0.0
            }

        stats = self.request_stats[request_id]
        stats["count"] += 1
        stats["total_time"] += execution_time
        stats["min_time"] = min(stats["min_time"], execution_time)
        stats["max_time"] = max(stats["max_time"], execution_time)

        if status_code < 400:
            stats["success_count"] += 1
        else:
            stats["error_count"] += 1

    def _log_performance(
        self,
        request: Request,
        execution_time: float,
        memory_used: float,
        status_code: int
    ):
        """Log performance information."""
        log_level = logging.INFO

        # Warn if request took too long
        if execution_time > 1.0:
            log_level = logging.WARNING
        # Error if request took very long
        elif execution_time > 5.0:
            log_level = logging.ERROR

        logger.log(
            log_level,
            f"{request.method} {request.url.path} - "
            f"Status: {status_code}, "
            f"Time: {execution_time:.4f}s, "
            f"Memory: {memory_used:.2f}MB"
        )

        # Detailed logging if enabled
        if self.enable_detailed_logging:
            logger.debug(
                f"Request details: "
                f"Client: {request.client.host if request.client else 'unknown'}, "
                f"User-Agent: {request.headers.get('user-agent', 'unknown')}"
            )

    def get_endpoint_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all endpoints."""
        result = {}

        for endpoint, stats in self.request_stats.items():
            if stats["count"] > 0:
                result[endpoint] = {
                    "request_count": stats["count"],
                    "avg_response_time": stats["total_time"] / stats["count"],
                    "min_response_time": stats["min_time"],
                    "max_response_time": stats["max_time"],
                    "success_rate": (stats["success_count"] / stats["count"]) * 100,
                    "error_count": stats["error_count"]
                }

        return result

    def get_slow_endpoints(self, threshold_seconds: float = 1.0) -> List[Dict[str, Any]]:
        """Get endpoints with average response time above threshold."""
        slow_endpoints = []

        for endpoint, stats in self.get_endpoint_stats().items():
            if stats["avg_response_time"] > threshold_seconds:
                slow_endpoints.append({
                    "endpoint": endpoint,
                    "avg_response_time": stats["avg_response_time"],
                    "request_count": stats["request_count"],
                    "max_response_time": stats["max_response_time"]
                })

        return sorted(slow_endpoints, key=lambda x: x["avg_response_time"], reverse=True)

    def reset_stats(self):
        """Reset all statistics."""
        self.request_stats.clear()


class RateLimitingMiddleware(BaseHTTPMiddleware):
    """Middleware to track and prevent rate limiting."""

    def __init__(self, app: ASGIApp, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.request_history: Dict[str, list] = {}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Check rate limits before processing request."""
        client_id = self._get_client_id(request)

        if self._is_rate_limited(client_id):
            return Response(
                content={"error": "Rate limit exceeded"},
                status_code=429,
                media_type="application/json"
            )

        # Record request
        self._record_request(client_id)

        # Process request
        return await call_next(request)

    def _get_client_id(self, request: Request) -> str:
        """Get client identifier for rate limiting."""
        # Use IP address or user ID if authenticated
        forward = request.headers.get("X-Forwarded-For")
        if forward:
            return forward.split(",")[0].strip()

        return str(request.client.host) if request.client else "unknown"

    def _record_request(self, client_id: str):
        """Record request timestamp."""
        if client_id not in self.request_history:
            self.request_history[client_id] = []

        self.request_history[client_id].append(time.time())

        # Clean old requests (older than 1 minute)
        cutoff = time.time() - 60
        self.request_history[client_id] = [
            ts for ts in self.request_history[client_id]
            if ts > cutoff
        ]

    def _is_rate_limited(self, client_id: str) -> bool:
        """Check if client has exceeded rate limit."""
        if client_id not in self.request_history:
            return False

        # Count requests in last minute
        cutoff = time.time() - 60
        recent_requests = [
            ts for ts in self.request_history[client_id]
            if ts > cutoff
        ]

        return len(recent_requests) >= self.requests_per_minute
