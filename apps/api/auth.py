import secrets
from fastapi import Request, HTTPException
from fastapi.security import APIKeyHeader
from starlette.middleware.base import BaseHTTPMiddleware
from packages.core.config import settings

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

class APIKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Allow OPTIONS for CORS
        if request.method == "OPTIONS":
            return await call_next(request)

        # Public endpoints (Health, Metrics, Docs)
        path = request.url.path
        if path in ["/health", "/metrics", "/docs", "/openapi.json", "/redoc", "/"]:
            return await call_next(request)

        # Verify API Key
        api_key = request.headers.get("X-API-Key")
        if not api_key or not secrets.compare_digest(api_key, settings.api_secret_key):
            # Check for query param as fallback (useful for browser/simple testing)
            api_key = request.query_params.get("api_key")
            if not api_key or not secrets.compare_digest(api_key, settings.api_secret_key):
                return await self._unauthorized_response()

        return await call_next(request)

    async def _unauthorized_response(self):
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=401,
            content={"detail": "Invalid or missing API Key"}
        )
