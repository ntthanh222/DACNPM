"""
Central error handling middleware for the application.

Provides consistent error responses and logging across all API endpoints.
"""

import logging
import traceback
from typing import Callable, Any
from fastapi import Request, status, Response
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as HTTPException

logger = logging.getLogger(__name__)

class ErrorResponse:
    """Standard error response format"""
    def __init__(self, error: str, message: str, status_code: int, details: dict = None):
        self.error = error
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        self.timestamp = None

def log_error(error: Exception, request: Request, context: dict = None):
    """
    Log errors with context and stack trace

    Args:
        error: The exception that occurred
        request: The HTTP request that caused the error
        context: Additional context information
    """
    error_info = {
        'error_type': type(error).__name__,
        'error_message': str(error),
        'method': request.method if request else "N/A",
        'path': request.url.path if request else "N/A",
        'query_params': dict(request.query_params) if request else {},
        'ip_address': request.client.host if (request and request.client) else None,
        'user_agent': request.headers.get('user-agent', 'Unknown') if request else 'Unknown',
        'timestamp': None
    }

    if context:
        error_info['context'] = context

    # Add stack trace for debugging (but don't include in logs in production)
    error_info['stack_trace'] = traceback.format_exc()

    # Log at different levels based on error type
    if isinstance(error, HTTPException):
        if error.status_code >= 500:
            logger.error(f"Server Error: {error_info}")
        else:
            logger.warning(f"Client Error: {error_info}")
    elif 'database' in str(error).lower() or 'connection' in str(error).lower():
        logger.warning(f"Database/Connection Error: {error_info}")
    else:
        logger.error(f"Unexpected Error: {error_info}")

async def exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Global exception handler for all HTTP exceptions

    Args:
        request: The HTTP request
        exc: The exception that occurred

    Returns:
        JSONResponse with standardized error format
    """
    error_type = type(exc).__name__
    error_message = str(exc)

    # Log the error
    log_error(exc, request)

    # Determine status code
    if isinstance(exc, HTTPException):
        status_code = exc.status_code
    elif 'database' in error_type.lower() or 'connection' in error_type.lower():
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    else:
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    # Prepare error response
    error_response = ErrorResponse(
        error=error_type,
        message=error_message,
        status_code=status_code
    )

    return JSONResponse(
        status_code=status_code,
        content={
            'error': error_response.error,
            'message': error_response.message,
            'details': error_response.details,
            'timestamp': error_response.timestamp
        }
    )

def setup_exception_handling(app):
    """
    Set up global exception handling in the FastAPI application

    Args:
        app: The FastAPI application instance
    """
    # Register global exception handler
    app.add_exception_handler(Exception, exception_handler)

    # Register specific exception handlers for common errors
    app.add_exception_handler(HTTPException, exception_handler)

    logger.info("✅ Global exception handling configured")

def catch_errors(func: Callable) -> Callable:
    """
    Decorator to catch and log errors in async functions

    Usage:
        @catch_errors
        async def my_function(request: Request):
            ...
    """
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            # Get request from args if available
            request = None
            if args and hasattr(args[0], 'request'):
                request = args[0].request

            log_error(e, request or None)
            raise
    return wrapper

def validate_params(required_params: list) -> Callable:
    """
    Decorator to validate required parameters

    Usage:
        @validate_params(['user_id', 'action'])
        async def my_function(user_id: str, action: str, optional_param: str = None):
            ...
    """
    def decorator(func: Callable) -> Callable:
        async def wrapper(*args, **kwargs):
            # Extract function signature
            import inspect
            sig = inspect.signature(func)

            # Get bound arguments
            bound_args = sig.bind(*args, **kwargs)

            # Validate required params
            for param_name in required_params:
                if param_name not in bound_args.arguments:
                    raise ValueError(f"Missing required parameter: {param_name}")

            return await func(*args, **kwargs)
        return wrapper
    return decorator

def safe_operation(default_value=None, raise_on_error=False):
    """
    Decorator to safely execute operations with fallback values

    Usage:
        @safe_operation(default_value="default", raise_on_error=True)
        async def my_function():
            risky_operation()
    """
    def decorator(func: Callable) -> Callable:
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                request = None
                if args and hasattr(args[0], 'request'):
                    request = args[0].request

                log_error(e, request or None)

                if raise_on_error:
                    raise
                return default_value
        return wrapper
    return decorator
