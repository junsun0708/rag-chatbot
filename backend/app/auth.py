import os

from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str = Security(API_KEY_HEADER)):
    """Verify API key from X-API-Key header.

    If API_KEY env var is not set, authentication is disabled (dev mode).
    """
    expected = os.getenv("API_KEY", "")
    if not expected:
        return
    if api_key != expected:
        raise HTTPException(status_code=403, detail="Invalid API Key")
