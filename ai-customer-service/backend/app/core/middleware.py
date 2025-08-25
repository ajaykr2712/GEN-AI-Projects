"""
Advanced API Middleware

This module provides comprehensive middleware for authentication, rate limiting,
monitoring, and security for the AI Customer Service API.
"""

import time
import json
import logging
from typing import Dict, Any, Optional, Callable
from datetime import datetime, timedelta
from collections import defaultdict, deque
import asyncio
import hashlib
import ipaddress

from fastapi import Request, Response, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.config import settings
from app.core.monitoring import metrics_collector

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware with configurable limits per endpoint."""
    
    def __init__(
        self,
        app: ASGIApp,
        default_rate_limit: int = 100,
        window_seconds: int = 60,
        burst_limit: int = 10
    ):
        super().__init__(app)
        self.default_rate_limit = default_rate_limit
        self.window_seconds = window_seconds
        self.burst_limit = burst_limit
        
        # Store request counts per client
        self._request_counts: Dict[str, deque] = defaultdict(lambda: deque())
        self._endpoint_limits: Dict[str, int] = {}
        self._whitelist_ips: set = set()
        
        # Configure specific endpoint limits
        self._configure_endpoint_limits()
    
    def _configure_endpoint_limits(self):
        """Configure rate limits for specific endpoints."""
        self._endpoint_limits = {
            "/api/v1/chat/chat": 20,  # AI chat endpoint - more restrictive
            "/api/v1/auth/login": 5,   # Login endpoint - very restrictive
            "/api/v1/auth/register": 3, # Registration endpoint
            "/health": 1000,           # Health check - very permissive
            "/metrics": 50             # Metrics endpoint
        }
    
    def add_whitelist_ip(self, ip: str):
        """Add IP to whitelist."""
        try:
            # Support both single IPs and CIDR networks
            if '/' in ip:
                network = ipaddress.ip_network(ip, strict=False)
                self._whitelist_ips.add(network)
            else:
                self._whitelist_ips.add(ipaddress.ip_address(ip))
            logger.info(f"Added IP to whitelist: {ip}")
        except ValueError as e:
            logger.error(f"Invalid IP address for whitelist: {ip} - {e}")
    
    def _is_whitelisted(self, client_ip: str) -> bool:
        """Check if client IP is whitelisted."""
        try:
            client_addr = ipaddress.ip_address(client_ip)
            for whitelist_item in self._whitelist_ips:
                if isinstance(whitelist_item, ipaddress.IPv4Network) or isinstance(whitelist_item, ipaddress.IPv6Network):
                    if client_addr in whitelist_item:
                        return True
                elif client_addr == whitelist_item:
                    return True
        except ValueError:
            pass
        return False
    
    def _get_client_identifier(self, request: Request) -> str:
        """Get unique identifier for the client."""
        # Try to get real IP from headers (for load balancer scenarios)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"
        
        # Include user ID if authenticated for more granular limiting
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            return f"user:{user_id}"
        
        return f"ip:{client_ip}"
    
    def _get_rate_limit(self, endpoint: str) -> int:
        """Get rate limit for specific endpoint."""
        return self._endpoint_limits.get(endpoint, self.default_rate_limit)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process rate limiting."""
        client_id = self._get_client_identifier(request)
        endpoint = request.url.path
        current_time = time.time()
        
        # Check if client is whitelisted
        client_ip = request.client.host if request.client else "unknown"
        if self._is_whitelisted(client_ip):
            return await call_next(request)
        
        # Get rate limit for this endpoint
        rate_limit = self._get_rate_limit(endpoint)
        
        # Clean old requests outside the time window
        window_start = current_time - self.window_seconds
        request_times = self._request_counts[client_id]
        
        while request_times and request_times[0] < window_start:
            request_times.popleft()
        
        # Check rate limit
        if len(request_times) >= rate_limit:
            # Record rate limit violation
            metrics_collector.record_counter(
                "rate_limit_violations",
                1,
                {"client_id": client_id, "endpoint": endpoint}
            )
            
            logger.warning(f"Rate limit exceeded for {client_id} on {endpoint}")
            
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Rate limit exceeded",
                    "retry_after": self.window_seconds,
                    "limit": rate_limit,
                    "window": self.window_seconds
                },
                headers={"Retry-After": str(self.window_seconds)}
            )
        
        # Add current request time
        request_times.append(current_time)
        
        # Record rate limiting metrics
        metrics_collector.record_gauge(
            "rate_limit_usage",
            len(request_times) / rate_limit,
            {"client_id": client_id, "endpoint": endpoint}
        )
        
        response = await call_next(request)
        
        # Add rate limit headers to response
        response.headers["X-RateLimit-Limit"] = str(rate_limit)
        response.headers["X-RateLimit-Remaining"] = str(max(0, rate_limit - len(request_times)))
        response.headers["X-RateLimit-Reset"] = str(int(current_time + self.window_seconds))
        
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Comprehensive request/response logging middleware."""
    
    def __init__(self, app: ASGIApp, log_body: bool = False, max_body_size: int = 1024):
        super().__init__(app)
        self.log_body = log_body
        self.max_body_size = max_body_size
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        request_id = self._generate_request_id(request)
        
        # Store request ID in state for use by other components
        request.state.request_id = request_id
        
        # Log request
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("User-Agent", "unknown")
        
        request_log = {
            "request_id": request_id,
            "method": request.method,
            "url": str(request.url),
            "client_ip": client_ip,
            "user_agent": user_agent,
            "headers": dict(request.headers),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Log request body if enabled (be careful with sensitive data)
        if self.log_body and request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                if len(body) <= self.max_body_size:
                    request_log["body"] = body.decode("utf-8", errors="ignore")
                else:
                    request_log["body"] = f"<truncated - size: {len(body)} bytes>"
            except Exception as e:
                request_log["body_error"] = str(e)
        
        logger.info(f"Request started: {json.dumps(request_log)}")
        
        # Process request
        try:
            response = await call_next(request)
            duration = time.time() - start_time
            
            # Log response
            response_log = {
                "request_id": request_id,
                "status_code": response.status_code,
                "duration": duration,
                "response_headers": dict(response.headers),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            logger.info(f"Request completed: {json.dumps(response_log)}")
            
            # Record metrics
            metrics_collector.record_timer(
                "request_duration",
                duration,
                {
                    "method": request.method,
                    "endpoint": request.url.path,
                    "status_code": str(response.status_code)
                }
            )
            
            metrics_collector.record_counter(
                "requests_total",
                1,
                {
                    "method": request.method,
                    "endpoint": request.url.path,
                    "status_code": str(response.status_code)
                }
            )
            
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            
            return response
        
        except Exception as e:
            duration = time.time() - start_time
            
            # Log error
            error_log = {
                "request_id": request_id,
                "error": str(e),
                "error_type": type(e).__name__,
                "duration": duration,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            logger.error(f"Request failed: {json.dumps(error_log)}")
            
            # Record error metrics
            metrics_collector.record_counter(
                "request_errors",
                1,
                {
                    "method": request.method,
                    "endpoint": request.url.path,
                    "error_type": type(e).__name__
                }
            )
            
            raise
    
    def _generate_request_id(self, request: Request) -> str:
        """Generate unique request ID."""
        # Use timestamp + client info for request ID
        timestamp = str(time.time())
        client_info = f"{request.client.host if request.client else 'unknown'}"
        request_info = f"{request.method}{request.url.path}"
        
        return hashlib.md5(f"{timestamp}{client_info}{request_info}".encode()).hexdigest()[:16]


class CacheMiddleware(BaseHTTPMiddleware):
    """Simple response caching middleware."""
    
    def __init__(self, app: ASGIApp, cache_ttl: int = 300):
        super().__init__(app)
        self.cache_ttl = cache_ttl
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cacheable_methods = {"GET"}
        self._cacheable_paths = {"/health", "/metrics"}
    
    def _get_cache_key(self, request: Request) -> str:
        """Generate cache key for request."""
        return hashlib.md5(f"{request.method}{request.url}".encode()).hexdigest()
    
    def _is_cacheable(self, request: Request) -> bool:
        """Check if request is cacheable."""
        return (
            request.method in self._cacheable_methods and
            any(request.url.path.startswith(path) for path in self._cacheable_paths)
        )
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not self._is_cacheable(request):
            return await call_next(request)
        
        cache_key = self._get_cache_key(request)
        current_time = time.time()
        
        # Check if we have a cached response
        if cache_key in self._cache:
            cached_item = self._cache[cache_key]
            if current_time - cached_item["timestamp"] < self.cache_ttl:
                # Return cached response
                metrics_collector.record_counter("cache_hits", 1, {"endpoint": request.url.path})
                
                response = JSONResponse(
                    content=cached_item["content"],
                    status_code=cached_item["status_code"]
                )
                response.headers["X-Cache"] = "HIT"
                return response
        
        # Not cached or expired, make request
        response = await call_next(request)
        
        # Cache successful responses
        if response.status_code == 200:
            try:
                # Read response body
                body = b""
                async for chunk in response.body_iterator:
                    body += chunk
                
                content = json.loads(body.decode())
                
                # Store in cache
                self._cache[cache_key] = {
                    "content": content,
                    "status_code": response.status_code,
                    "timestamp": current_time
                }
                
                # Clean old cache entries periodically
                if len(self._cache) > 1000:  # Limit cache size
                    self._cleanup_cache(current_time)
                
                metrics_collector.record_counter("cache_misses", 1, {"endpoint": request.url.path})
                
                # Create new response with cached content
                new_response = JSONResponse(content=content, status_code=response.status_code)
                new_response.headers.update(response.headers)
                new_response.headers["X-Cache"] = "MISS"
                return new_response
                
            except Exception as e:
                logger.warning(f"Failed to cache response: {e}")
        
        response.headers["X-Cache"] = "SKIP"
        return response
    
    def _cleanup_cache(self, current_time: float):
        """Remove expired cache entries."""
        expired_keys = [
            key for key, item in self._cache.items()
            if current_time - item["timestamp"] > self.cache_ttl
        ]
        for key in expired_keys:
            del self._cache[key]
        
        logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")


class CORSMiddleware(BaseHTTPMiddleware):
    """Enhanced CORS middleware with security features."""
    
    def __init__(
        self,
        app: ASGIApp,
        allowed_origins: list = None,
        allowed_methods: list = None,
        allowed_headers: list = None,
        expose_headers: list = None,
        allow_credentials: bool = False,
        max_age: int = 86400
    ):
        super().__init__(app)
        self.allowed_origins = allowed_origins or ["*"]
        self.allowed_methods = allowed_methods or ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
        self.allowed_headers = allowed_headers or ["*"]
        self.expose_headers = expose_headers or []
        self.allow_credentials = allow_credentials
        self.max_age = max_age
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        origin = request.headers.get("Origin")
        
        # Handle preflight requests
        if request.method == "OPTIONS":
            response = Response()
            self._add_cors_headers(response, origin)
            return response
        
        response = await call_next(request)
        self._add_cors_headers(response, origin)
        return response
    
    def _add_cors_headers(self, response: Response, origin: str = None):
        """Add CORS headers to response."""
        if origin and self._is_origin_allowed(origin):
            response.headers["Access-Control-Allow-Origin"] = origin
        elif "*" in self.allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = "*"
        
        response.headers["Access-Control-Allow-Methods"] = ", ".join(self.allowed_methods)
        response.headers["Access-Control-Allow-Headers"] = ", ".join(self.allowed_headers)
        
        if self.expose_headers:
            response.headers["Access-Control-Expose-Headers"] = ", ".join(self.expose_headers)
        
        if self.allow_credentials:
            response.headers["Access-Control-Allow-Credentials"] = "true"
        
        response.headers["Access-Control-Max-Age"] = str(self.max_age)
    
    def _is_origin_allowed(self, origin: str) -> bool:
        """Check if origin is allowed."""
        return origin in self.allowed_origins or "*" in self.allowed_origins
