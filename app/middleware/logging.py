import time
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from loguru import logger
import uuid

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging request and response details.
    
    Logs the following information:
    - Request ID (for tracing)
    - HTTP method
    - URL path
    - Client IP
    - Status code
    - Processing time
    - User agent
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next):
        # Generate unique request ID for tracing
        request_id = str(uuid.uuid4())
        
        # Extract request details
        method = request.method
        path = request.url.path
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "Unknown")
        
        # Log request start
        logger.info(f"Request started | ID: {request_id} | {method} {path} | IP: {client_ip} | UA: {user_agent}")
        
        # Record start time
        start_time = time.time()
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Log request completion
            logger.info(
                f"Request completed | ID: {request_id} | {method} {path} | "
                f"Status: {response.status_code} | Time: {process_time:.4f}s"
            )
            
            # Add request ID to response headers for tracing
            response.headers["X-Request-ID"] = request_id
            
            return response
            
        except Exception as e:
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Log error
            logger.error(
                f"Request failed | ID: {request_id} | {method} {path} | "
                f"Error: {str(e)} | Time: {process_time:.4f}s"
            )
            
            # Re-raise the exception
            raise
    
    def _get_client_ip(self, request: Request) -> str:
        # Try to get IP from X-Forwarded-For header first (for proxies)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        # Fall back to client.host
        return request.client.host if request.client else "unknown"