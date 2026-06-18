# FastAPI imports are lazy — inside register_exception_handlers() below.
# This allows the exception classes to be imported without FastAPI installed
# (important for unit tests that only need the exception types).


# ── Base Exception ──────────────────────────────────────────────

class AIServerException(Exception):
    """Base exception for all AI Server errors."""
    def __init__(self, message: str, status_code: int = 500, errors: list = None):
        self.message = message
        self.status_code = status_code
        self.errors = errors or []
        super().__init__(self.message)


# ── Existing Exceptions ─────────────────────────────────────────

class LLMProviderException(AIServerException):
    """Raised when all LLM providers fail or have outages."""
    def __init__(self, message: str, errors: list = None):
        super().__init__(message=message, status_code=502, errors=errors)


class RAGException(AIServerException):
    """Raised during RAG document indexing or retrieval failures."""
    def __init__(self, message: str, errors: list = None):
        super().__init__(message=message, status_code=500, errors=errors)


class SecurityException(AIServerException):
    """Raised during API key validation or authentication failures."""
    def __init__(self, message: str):
        super().__init__(message=message, status_code=401)


# ── Voice Exceptions ────────────────────────────────────────────

class VoiceProviderException(AIServerException):
    """Raised when a voice provider (STT/TTS) fails.

    The gateway catches this and chains to the fallback provider.
    Engines MUST raise this on failure — never return a degraded result.
    """
    def __init__(self, message: str, status_code: int = 503, errors: list = None):
        super().__init__(message=message, status_code=status_code, errors=errors)


class AudioValidationError(AIServerException):
    """Raised when audio input fails validation checks.

    Carries a stable error_code for the frontend to handle.
    """
    def __init__(self, error_code: str, status_code: int = 400, errors: list = None):
        self.error_code = error_code
        super().__init__(
            message=error_code.replace("_", " ").title(),
            status_code=status_code,
            errors=errors,
        )


class SessionExpiredError(AIServerException):
    """Raised when an interview session has expired or doesn't exist."""
    def __init__(self, message: str = "session_not_found"):
        super().__init__(message=message, status_code=401)


class DraftExpiredError(AIServerException):
    """Raised when a draft has expired or was already consumed."""
    def __init__(self, message: str = "draft_expired"):
        super().__init__(message=message, status_code=410)


class ConfirmConflictError(AIServerException):
    """Raised when a draft was already confirmed for this session."""
    def __init__(self, message: str = "confirm_conflict"):
        super().__init__(message=message, status_code=409)


# ── Exception Handlers ──────────────────────────────────────────

def register_exception_handlers(app) -> None:
    from fastapi import FastAPI, Request
    from fastapi.responses import JSONResponse
    from fastapi.exceptions import RequestValidationError
    from starlette.exceptions import HTTPException as StarletteHTTPException

    @app.exception_handler(AIServerException)
    async def ai_server_exception_handler(request: Request, exc: AIServerException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "message": exc.message,
                "data": None,
                "errors": exc.errors,
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        errors = [
            {"loc": err["loc"], "msg": err["msg"], "type": err["type"]}
            for err in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "message": "Input validation error",
                "data": None,
                "errors": errors,
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "message": exc.detail,
                "data": None,
                "errors": [],
            },
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "Internal Server Error",
                "data": None,
                "errors": [str(exc)],
            },
        )
