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
    
    if not secrets.compare_digest(api_key, settings.AI_SERVER_API_KEY):
        raise SecurityException("Invalid API Key.")
        
    return api_key
