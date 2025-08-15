from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Dict, Tuple, Optional, Callable
import time
from collections import defaultdict
from app.config.config import settings
from loguru import logger

class RateLimiter(BaseHTTPMiddleware):
    def __init__(self, app, rate_limit_per_minute: int = None, exclude_paths: list = None):
        super().__init__(app)
        self.rate_limit_per_minute = rate_limit_per_minute or settings.RATE_LIMIT_REQUESTS
        self.exclude_paths = exclude_paths or ['/docs', '/redoc', '/openapi.json']
        self.request_counts: Dict[str, Dict[float, int]] = defaultdict(lambda: defaultdict(int))
        self.window_size = 60  # 1 minute in seconds
        
        logger.info(f"Rate limiter initialized with {self.rate_limit_per_minute} requests per minute")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)
        
        # Get client IP
        client_ip = self._get_client_ip(request)
        
        # Check rate limit
        current_time = time.time()
        self._cleanup_old_requests(client_ip, current_time)
        
        # Count requests in the current window
        request_count = self._count_requests(client_ip, current_time)
        
        # If rate limit exceeded, return 429 Too Many Requests
        if request_count > self.rate_limit_per_minute:
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later."
            )
        
        # Increment request count for this window
        window_key = current_time // self.window_size * self.window_size
        self.request_counts[client_ip][window_key] += 1
        
        # Process the request
        response = await call_next(request)
        
        # Add rate limit headers
        remaining = max(0, self.rate_limit_per_minute - request_count)
        response.headers["X-RateLimit-Limit"] = str(self.rate_limit_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(window_key + self.window_size))
        
        return response

    def _get_client_ip(self, request: Request) -> str:
        # Try to get IP from X-Forwarded-For header first (for proxies)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        # Fall back to client.host
        return request.client.host if request.client else "unknown"

    def _cleanup_old_requests(self, client_ip: str, current_time: float) -> None:
        # Remove windows older than window_size seconds
        if client_ip in self.request_counts:
            current_window = current_time // self.window_size * self.window_size
            self.request_counts[client_ip] = {
                window: count 
                for window, count in self.request_counts[client_ip].items() 
                if window >= current_window - self.window_size
            }

    def _count_requests(self, client_ip: str, current_time: float) -> int:
        # Count all requests in the current window
        if client_ip not in self.request_counts:
            return 0
        
        current_window = current_time // self.window_size * self.window_size
        return sum(
            count 
            for window, count in self.request_counts[client_ip].items() 
            if window >= current_window - self.window_size
        )