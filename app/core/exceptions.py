from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

class AIServerException(Exception):
    """Base exception for all AI Server errors"""
    def __init__(self, message: str, status_code: int = 500, errors: list = None):
        self.message = message
        self.status_code = status_code
        self.errors = errors or []
        super().__init__(self.message)

class LLMProviderException(AIServerException):
    """Raised when all LLM providers fail or have outages"""
    def __init__(self, message: str, errors: list = None):
        super().__init__(message=message, status_code=502, errors=errors)

class RAGException(AIServerException):
    """Raised during RAG document indexing or retrieval failures"""
    def __init__(self, message: str, errors: list = None):
        super().__init__(message=message, status_code=500, errors=errors)

class SecurityException(AIServerException):
    """Raised during API key validation or authentication failures"""
    def __init__(self, message: str):
        super().__init__(message=message, status_code=401)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AIServerException)
    async def ai_server_exception_handler(request: Request, exc: AIServerException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "message": exc.message,
                "data": None,
                "errors": exc.errors
            }
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        errors = [{"loc": err["loc"], "msg": err["msg"], "type": err["type"]} for err in exc.errors()]
        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "message": "Input validation error",
                "data": None,
                "errors": errors
            }
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "message": exc.detail,
                "data": None,
                "errors": []
            }
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "Internal Server Error",
                "data": None,
                "errors": [str(exc)]
            }
        )
