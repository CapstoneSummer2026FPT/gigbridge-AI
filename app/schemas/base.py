"""
PURPOSE: Standardized API response wrappers for API endpoints.
IMPORTANCE: Critical — Primary response wrapper model used across all FastAPI routes.
READING FLOW: app/schemas/base.py -> app/api/routes/*.py
"""

from typing import Generic, TypeVar, Optional, List
from pydantic import BaseModel

T = TypeVar('T')

class StandardResponse(BaseModel, Generic[T]):
    """Standardized API response wrapper"""
    success: bool
    message: str
    data: Optional[T] = None
    errors: Optional[List[str]] = None
