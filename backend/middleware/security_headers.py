"""
Security middleware to add security headers to responses.

This middleware adds various security headers to protect against common web vulnerabilities.
"""

import logging
from fastapi import Request, Response

logger = logging.getLogger(__name__)


def add_security_headers(response: Response, request: Request = None) -> Response:
    """
    Add security headers to response.

    Args:
        response: FastAPI Response object
        request: FastAPI Request object (optional, for referer checks)

    Returns:
        Response with security headers added
    """
    # Content Security Policy - Strengthened security configuration
    # Removed 'unsafe-inline' and 'unsafe-eval' from script-src to prevent XSS attacks
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "  # Allow CDN for DOMPurify and other trusted libraries
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "  # unsafe-inline needed for inline styles in development
        "img-src 'self' data: https://*.googleusercontent.com https://cdn.jsdelivr.net; "  # Allow trusted image sources
        "connect-src 'self' https://*.supabase.co wss://*.supabase.co; "  # WebSocket support
        "font-src 'self' https://fonts.gstatic.com https://fonts.googleapis.com data:; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "frame-ancestors 'none'; "  # Prevent clickjacking
        "require-trusted-types-for 'script'; "  # Additional security layer
        "trusted-types * dompurify"  # Allow DOMPurify for HTML sanitization
    )

    # XSS Protection
    response.headers['X-XSS-Protection'] = '1; mode=block'

    # Referrer Policy
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'

    # Frame Options
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'

    # Permissions Policy
    response.headers['Permissions-Policy'] = (
        'geolocation=(), '
        'microphone=(), '
        'camera=(), '
        'payment=(), '
        'usb=(), '
        'magnetometer=(), '
        'gyroscope=(), '
        'accelerometer=(), '
        'clipboard-read=(), '
        'clipboard-write=(), '
        'autoplay=(), '
        'focus-without-user-activation=()'
    )

    # Security headers for older browsers
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'

    # Remove X-Powered-By header
    response.headers.pop('X-Powered-By', None)

    return response


async def security_middleware(request: Request, call_next):
    """
    FastAPI middleware to add security headers to all responses.

    Args:
        request: FastAPI Request object
        call_next: Next middleware in chain

    Returns:
        Response with security headers added
    """
    response = await call_next(request)

    # Add security headers to all responses
    add_security_headers(response, request)

    return response


class SecurityHeadersMiddleware:
    """
    Middleware for adding security headers.

    Usage:
        app.add_middleware(SecurityHeadersMiddleware)
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        """
        Process request and response with security headers.

        Args:
            scope: ASGI scope
            receive: ASGI receive callable
            send: ASGI send callable
        """
        async def modified_send(message):
            # Modify response headers if this is a response message
            if message.get('type') == 'http.response.start':
                # Add security headers to response
                headers = dict(message.get('headers', []))

                # CSP header - Strengthened configuration
                if 'content-security-policy' not in headers:
                    headers.append((b'Content-Security-Policy',
                                   b"default-src 'self'; script-src 'self' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; img-src 'self' data: https://*.googleusercontent.com https://cdn.jsdelivr.net; connect-src 'self' https://*.supabase.co wss://*.supabase.co; font-src 'self' https://fonts.gstatic.com https://fonts.googleapis.com data:; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'; require-trusted-types-for 'script'; trusted-types * dompurify"))

                # XSS Protection
                if 'x-xss-protection' not in headers:
                    headers.append((b'X-XSS-Protection', b'1; mode=block'))

                # Referrer Policy
                if 'referrer-policy' not in headers:
                    headers.append((b'Referrer-Policy', b'strict-origin-when-cross-origin'))

                # X-Frame-Options
                if 'x-frame-options' not in headers:
                    headers.append((b'X-Frame-Options', b'SAMEORIGIN'))

                # Permissions Policy
                if 'permissions-policy' not in headers:
                    headers.append((b'Permissions-Policy',
                                   b'geolocation=(), microphone=(), camera=(), payment=(), usb=(), magnetometer=(), gyroscope=(), accelerometer=(), clipboard-read=(), clipboard-write=(), autoplay=(), focus-without-user-activation=()'))

                # X-Content-Type-Options
                if 'x-content-type-options' not in headers:
                    headers.append((b'X-Content-Type-Options', b'nosniff'))

                # HSTS
                if 'strict-transport-security' not in headers:
                    headers.append((b'Strict-Transport-Security', b'max-age=31536000; includeSubDomains; preload'))

                # Remove X-Powered-By
                headers = [(k, v) for k, v in headers if k.lower() != b'x-powered-by']

                message['headers'] = headers

            await send(message)

        await self.app(scope, receive, modified_send)
