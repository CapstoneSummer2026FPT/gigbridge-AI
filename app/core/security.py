import secrets

from fastapi import Security
from fastapi.security import APIKeyHeader
from app.core.config import settings
from app.core.exceptions import SecurityException

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_api_key(api_key: str = Security(API_KEY_HEADER)) -> str:
    """
    Verifies that the provided API key matches the server's configured key.
    """
    if not api_key:
        raise SecurityException("API Key missing in request headers.")
    
    server_key = settings.AI_SERVER_API_KEY.strip() if settings.AI_SERVER_API_KEY else ""
    
    if not server_key:
        if settings.APP_ENV != "production":
            return api_key
        raise SecurityException("API Key not configured on server.")

    if not secrets.compare_digest(api_key, server_key):
        raise SecurityException("Invalid API Key.")
        
    return api_key

