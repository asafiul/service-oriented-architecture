import time
import uuid
import json
import logging
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import Message
from typing import Callable
from datetime import datetime

logger = logging.getLogger("api")

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        start_time = time.time()
        
        body = None
        if request.method in ["POST", "PUT", "DELETE"]:
            body = await self._get_body(request)
        
        response = await call_next(request)
        
        duration_ms = (time.time() - start_time) * 1000
        
        user_id = request.headers.get("X-User-Id", None)
        
        log_data = {
            "request_id": request_id,
            "method": request.method,
            "endpoint": str(request.url.path),
            "status_code": response.status_code,
            "duration_ms": round(duration_ms, 2),
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        if body and request.method in ["POST", "PUT", "DELETE"]:
            log_data["request_body"] = self._mask_sensitive_data(body)
        
        logger.info(json.dumps(log_data, ensure_ascii=False))
        
        response.headers["X-Request-Id"] = request_id
        
        return response
    
    async def _get_body(self, request: Request) -> dict:
        try:
            body = await request.body()
            if body:
                return json.loads(body.decode())
        except:
            pass
        return None
    
    def _mask_sensitive_data(self, data: dict) -> dict:
        if not isinstance(data, dict):
            return data
        
        masked = data.copy()
        sensitive_fields = ["password", "token", "secret", "api_key"]
        
        for key in masked:
            if any(field in key.lower() for field in sensitive_fields):
                masked[key] = "***MASKED***"
        
        return masked
