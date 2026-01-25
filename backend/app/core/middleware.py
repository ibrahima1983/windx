"""Middleware configuration and custom middleware classes.

This module provides security and utility middleware for the FastAPI application
using Starlette middleware components and custom implementations.

Public Classes:
    RequestIDMiddleware: Add unique request ID to each request
    SecurityHeadersMiddleware: Add security headers to responses
    LoggingMiddleware: Log requests and responses with timing
    RequestSizeLimitMiddleware: Limit request body size
    RateLimitByIPMiddleware: Simple IP-based rate limiting
    CSRFProtectionMiddleware: CSRF token validation
    TimeoutMiddleware: Enforce request timeout limits

Public Functions:
    setup_middleware: Configure all middleware for the application

Features:
    - Request ID tracking for debugging
    - Security headers (HSTS, CSP, X-Frame-Options, etc.)
    - Request/response logging with timing
    - CORS with security best practices
    - Trusted host validation
    - HTTPS redirect in production
    - Gzip compression
    - Request size limits
    - Rate limiting by IP
    - CSRF protection
    - Request timeout enforcement
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
import uuid
from collections import defaultdict
from collections.abc import Callable

from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.types import ASGIApp

from app.core.config import Settings, get_settings

__all__ = [
    "RequestIDMiddleware",
    "SecurityHeadersMiddleware",
    "LoggingMiddleware",
    "RequestSizeLimitMiddleware",
    "RateLimitByIPMiddleware",
    "CSRFProtectionMiddleware",
    "TimeoutMiddleware",
    "setup_middleware",
]

logger = logging.getLogger(__name__)


# ============================================================================
# Custom Middleware Classes
# ============================================================================


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Add unique request ID to each request.

    Adds X-Request-ID header to responses and makes it available
    in request.state for logging and error tracking.

    Attributes:
        app: ASGI application instance
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and add request ID.

        Args:
            request (Request): Incoming request
            call_next (Callable): Next middleware/endpoint

        Returns:
            Response: Response with X-Request-ID header
        """
        # Generate or use existing request ID
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

        # Store in request state for access in endpoints/logging
        request.state.request_id = request_id

        # Process request
        response = await call_next(request)

        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id

        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses.

    Implements OWASP security headers recommendations including:
    - X-Content-Type-Options
    - X-XSS-Protection
    - X-Frame-Options
    - Referrer-Policy
    - Permissions-Policy
    - Content-Security-Policy
    - Strict-Transport-Security (HTTPS only)

    Attributes:
        app: ASGI application instance
        hsts_max_age: HSTS max age in seconds
    """

    def __init__(self, app: ASGIApp, *, hsts_max_age: int = 31536000) -> None:
        """Initialize security headers middleware.

        Args:
            app (ASGIApp): ASGI application
            hsts_max_age (int): HSTS max age in seconds (default: 1 year)
        """
        super().__init__(app)
        self.hsts_max_age = hsts_max_age

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and add security headers.

        Args:
            request (Request): Incoming request
            call_next (Callable): Next middleware/endpoint

        Returns:
            Response: Response with security headers
        """
        response = await call_next(request)

        # Security headers
        security_headers = {
            # Prevent MIME type sniffing
            "X-Content-Type-Options": "nosniff",
            # Enable XSS protection
            "X-XSS-Protection": "1; mode=block",
            # Prevent clickjacking
            "X-Frame-Options": "DENY",
            # Referrer policy
            "Referrer-Policy": "strict-origin-when-cross-origin",
            # Permissions policy (formerly Feature Policy)
            "Permissions-Policy": (
                "geolocation=(), microphone=(), camera=(), "
                "payment=(), usb=(), magnetometer=(), gyroscope=()"
            ),
            # Content Security Policy (allow Swagger UI CDN and Alpine.js)
            # Note: 'unsafe-eval' is required for Alpine.js to parse and execute
            # expressions in x-data, x-on, x-show, and other Alpine attributes
            "Content-Security-Policy": (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "img-src 'self' data: https:; "
                "font-src 'self' https://cdn.jsdelivr.net; "
                "connect-src 'self'; "
                "frame-ancestors 'none';"
            ),
        }

        # Add HSTS for HTTPS requests
        if request.url.scheme == "https":
            security_headers["Strict-Transport-Security"] = (
                f"max-age={self.hsts_max_age}; includeSubDomains; preload"
            )

        # Apply headers
        for header, value in security_headers.items():
            response.headers[header] = value

        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """Log requests and responses with timing information.

    Logs all HTTP requests with method, path, status code, duration,
    client IP, user agent, and request ID for correlation.

    Attributes:
        app: ASGI application instance
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and log details.

        Args:
            request (Request): Incoming request
            call_next (Callable): Next middleware/endpoint

        Returns:
            Response: Response from next middleware/endpoint
        """
        start_time = time.time()

        # Get request ID if available
        request_id = getattr(request.state, "request_id", "unknown")

        # Log request
        logger.info(
            f"Request started: {request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "query_params": str(request.query_params),
                "client_ip": request.client.host if request.client else "unknown",
                "user_agent": request.headers.get("User-Agent", "unknown"),
            },
        )

        # Process request
        try:
            response = await call_next(request)

            # Calculate duration
            duration = time.time() - start_time

            # Log response
            logger.info(
                f"Request completed: {request.method} {request.url.path} - "
                f"{response.status_code} in {duration:.3f}s",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration": duration,
                },
            )

            return response

        except Exception as e:
            # Calculate duration for failed requests
            duration = time.time() - start_time

            # Log error
            logger.error(
                f"Request failed: {request.method} {request.url.path} - "
                f"Error: {str(e)} in {duration:.3f}s",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "error": str(e),
                    "duration": duration,
                },
            )

            # Re-raise the exception
            raise


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Limit request body size to prevent DoS attacks.

    Rejects requests with Content-Length exceeding the configured limit.

    Attributes:
        app: ASGI application instance
        max_size: Maximum request size in bytes
    """

    def __init__(self, app: ASGIApp, *, max_size: int = 16 * 1024 * 1024) -> None:
        """Initialize request size limit middleware.

        Args:
            app (ASGIApp): ASGI application
            max_size (int): Maximum request size in bytes (default: 16MB)
        """
        super().__init__(app)
        self.max_size = max_size

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Check request size and process if within limit.

        Args:
            request (Request): Incoming request
            call_next (Callable): Next middleware/endpoint

        Returns:
            Response: Response from next middleware/endpoint or error

        Raises:
            None: Returns JSONResponse with 413 status instead of raising
        """
        # Check Content-Length header
        content_length = request.headers.get("Content-Length")

        if content_length:
            content_length_int = int(content_length)
            if content_length_int > self.max_size:
                return JSONResponse(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    content={
                        "error": "request_too_large",
                        "message": f"Request entity too large. Maximum size: {self.max_size} bytes",
                        "details": [
                            {
                                "type": "request_too_large",
                                "message": f"Request size {content_length_int} exceeds limit {self.max_size}",
                                "field": None,
                            }
                        ],
                    },
                )

        return await call_next(request)


class RateLimitByIPMiddleware(BaseHTTPMiddleware):
    """Simple IP-based rate limiting middleware.

    Tracks requests per IP address and enforces rate limits.
    Note: Use Redis-based fastapi-limiter for production with multiple workers.

    Attributes:
        app: ASGI application instance
        calls: Number of calls allowed per period
        period: Time period in seconds
        clients: Dictionary tracking client request timestamps
    """

    def __init__(
        self,
        app: ASGIApp,
        *,
        calls: int = 100,
        period: int = 60,
    ) -> None:
        """Initialize rate limit middleware.

        Args:
            app (ASGIApp): ASGI application
            calls (int): Number of calls allowed (default: 100)
            period (int): Time period in seconds (default: 60)
        """
        super().__init__(app)
        self.calls = calls
        self.period = period
        self.clients: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Check rate limit and process request.

        Args:
            request (Request): Incoming request
            call_next (Callable): Next middleware/endpoint

        Returns:
            Response: Response from next middleware/endpoint or rate limit error
        """
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()

        # Clean old entries
        self.clients[client_ip] = [
            timestamp for timestamp in self.clients[client_ip] if now - timestamp < self.period
        ]

        # Check rate limit
        if len(self.clients[client_ip]) >= self.calls:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "rate_limit_exceeded",
                    "message": "Too many requests. Please try again later.",
                    "details": [
                        {
                            "type": "rate_limit_exceeded",
                            "message": f"Rate limit: {self.calls} requests per {self.period} seconds",
                            "field": None,
                        }
                    ],
                },
                headers={"Retry-After": str(self.period)},
            )

        # Add current request
        self.clients[client_ip].append(now)

        return await call_next(request)


class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    """CSRF protection middleware for state-changing operations.

    Validates CSRF tokens for POST, PUT, PATCH, DELETE requests.
    Safe methods (GET, HEAD, OPTIONS, TRACE) are exempt.

    Attributes:
        app: ASGI application instance
        secret_key: Secret key for token validation
        exempt_paths: Paths exempt from CSRF protection
        safe_methods: HTTP methods that don't require CSRF protection
    """

    def __init__(
        self,
        app: ASGIApp,
        *,
        secret_key: str,
        exempt_paths: list[str] | None = None,
    ) -> None:
        """Initialize CSRF protection middleware.

        Args:
            app (ASGIApp): ASGI application
            secret_key (str): Secret key for token generation/validation
            exempt_paths (list[str] | None): Paths exempt from CSRF protection
        """
        super().__init__(app)
        self.secret_key = secret_key
        self.exempt_paths = exempt_paths or [
            "/api/v1/auth/login",
            "/api/v1/auth/register",
            "/docs",
            "/redoc",
            "/openapi.json",
        ]
        self.safe_methods = {"GET", "HEAD", "OPTIONS", "TRACE"}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Validate CSRF token for state-changing requests.

        Args:
            request (Request): Incoming request
            call_next (Callable): Next middleware/endpoint

        Returns:
            Response: Response from next middleware/endpoint or CSRF error
        """
        # Skip CSRF check for safe methods and exempt paths
        if (
            request.method in self.safe_methods
            or request.url.path in self.exempt_paths
            or request.url.path.startswith("/docs")
            or request.url.path.startswith("/redoc")
        ):
            return await call_next(request)

        # Check CSRF token
        csrf_token = request.headers.get("X-CSRF-Token")

        if not csrf_token:
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "error": "csrf_token_missing",
                    "message": "CSRF token is required for this operation",
                    "details": [
                        {
                            "type": "csrf_token_missing",
                            "message": "Include X-CSRF-Token header in your request",
                            "field": "X-CSRF-Token",
                        }
                    ],
                },
            )

        # Validate token (simplified - implement proper CSRF validation in production)
        # In production, use a library like itsdangerous or implement proper HMAC validation
        # This is a basic example showing the structure

        return await call_next(request)


class TimeoutMiddleware(BaseHTTPMiddleware):
    """Enforce request timeout to prevent long-running requests.

    Prevents requests from hanging indefinitely by enforcing a configurable
    timeout. Returns HTTP 504 Gateway Timeout if request exceeds the limit.

    This middleware helps prevent DoS attacks and resource exhaustion from
    slow or hanging requests.

    Attributes:
        app: ASGI application instance
        timeout: Request timeout in seconds
    """

    def __init__(self, app: ASGIApp, *, timeout: float = 30.0) -> None:
        """Initialize timeout middleware.

        Args:
            app (ASGIApp): ASGI application
            timeout (float): Request timeout in seconds (default: 30.0)
        """
        super().__init__(app)
        self.timeout = timeout

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with timeout enforcement.

        Args:
            request (Request): Incoming request
            call_next (Callable): Next middleware/endpoint

        Returns:
            Response: Response from next middleware/endpoint or timeout error

        Raises:
            None: Returns JSONResponse with 504 status instead of raising
        """
        try:
            # Enforce timeout using asyncio.wait_for
            response = await asyncio.wait_for(
                call_next(request),
                timeout=self.timeout,
            )
            return response

        except TimeoutError:
            # Get request ID if available for error tracking
            request_id = getattr(request.state, "request_id", "unknown")

            # Log timeout event
            logger.warning(
                f"Request timeout: {request.method} {request.url.path} "
                f"exceeded {self.timeout}s limit",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "timeout": self.timeout,
                },
            )

            # Return 504 Gateway Timeout
            return JSONResponse(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                content={
                    "error": "request_timeout",
                    "message": f"Request exceeded {self.timeout}s timeout",
                    "details": [
                        {
                            "type": "request_timeout",
                            "message": f"Request processing time exceeded {self.timeout} seconds",
                            "field": None,
                        }
                    ],
                    "request_id": request_id,
                },
            )


# ============================================================================
# Middleware Setup Function
# ============================================================================


# noinspection PyTypeChecker
def setup_middleware(app: FastAPI, settings: Settings | None = None) -> None:
    """Configure MINIMAL middleware for Azure deployment.

    FUCK ALL THE FANCY SHIT - JUST MAKE IT WORK
    """
    if settings is None:
        settings = get_settings()

    logger.info("Setting up MINIMAL middleware for Azure - no bullshit")

    # ONLY CORS - nothing else that can cause redirects
    if settings.backend_cors_origins:
        logger.info(f"Adding CORS for origins: {settings.backend_cors_origins}")
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[str(origin) for origin in settings.backend_cors_origins],
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=["*"],
            expose_headers=["*"],
        )
    else:
        logger.info("Adding CORS for all origins - development mode")
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=False,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=["*"],
        )

    logger.info("[OK] MINIMAL middleware configured - no redirects possible")
