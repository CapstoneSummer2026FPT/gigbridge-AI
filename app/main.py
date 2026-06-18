import asyncio
import logging
import sys

import redis.asyncio as aioredis
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.security import verify_api_key
from app.api.routes import job_posts, interviews, matching, analysis

logger = logging.getLogger("ai_server")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

app = FastAPI(
    title="GigBridge AI Service",
    description="Stand-alone Microservice providing NLP and AI intelligence to GigBridge platform.",
    version="1.0.0",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register exceptions
register_exception_handlers(app)

# Include routers (protected by default)
app.include_router(
    job_posts.router,
    prefix="/api/ai",
    tags=["Job Posts"],
    dependencies=[Depends(verify_api_key)],
)
app.include_router(
    interviews.router,
    prefix="/api/ai",
    tags=["AI Interviews"],
    dependencies=[Depends(verify_api_key)],
)
app.include_router(
    matching.router,
    prefix="/api/ai",
    tags=["Talent Matching"],
    dependencies=[Depends(verify_api_key)],
)
app.include_router(
    analysis.router,
    prefix="/api/ai",
    tags=["AI Analysis"],
    dependencies=[Depends(verify_api_key)],
)


@app.on_event("startup")
async def validate_voice_dependencies():
    """Validate voice service dependencies at startup.

    Fails fast if Redis is unavailable (no session state = no interview flow).
    Warns if Google credentials are missing (STT/TTS fallback limited).
    Validates Faster-Whisper only if configured as active provider.
    """
    errors: list[str] = []

    # 1. Redis — fail fast (mandatory for all interview flows)
    try:
        redis_client = aioredis.from_url(settings.REDIS_URL)
        await redis_client.ping()
        await redis_client.aclose()
        logger.info("✓ Redis connection OK (%s)", settings.REDIS_URL)
    except Exception as exc:
        errors.append(f"Redis unavailable: {exc}")
        logger.critical(
            "STARTUP FAILED: Redis is required for session state — %s", exc
        )
        sys.exit(1)

    # 2. Faster-Whisper — only check if configured as active provider
    if settings.STT_PRIMARY_PROVIDER == "faster_whisper" or settings.STT_FALLBACK_PROVIDER == "faster_whisper":
        try:
            import faster_whisper as _  # noqa: F401 — verify package exists

            logger.info(
                "✓ Faster-Whisper package found (model will lazy-load on first call)"
            )
        except ImportError:
            logger.critical(
                "STT_PRIMARY_PROVIDER or STT_FALLBACK_PROVIDER is 'faster_whisper' "
                "but the package is not installed. Run: pip install faster-whisper"
            )
            sys.exit(1)
    else:
        logger.info("• Faster-Whisper not configured — using Google STT as primary")

    # 3. Google credentials — warn only (fallback still works)
    if not settings.GOOGLE_APPLICATION_CREDENTIALS:
        logger.warning(
            "⚠ GOOGLE_APPLICATION_CREDENTIALS not set — "
            "Google STT/TTS providers will raise at runtime if called. "
            "Set this env var to enable Google Cloud voice services."
        )
    else:
        logger.info(
            "✓ Google credentials found at: %s",
            settings.GOOGLE_APPLICATION_CREDENTIALS,
        )

    # 4. PyAV — check availability (critical for audio decode)
    try:
        import av as _  # noqa: F401

        logger.info("✓ PyAV (av) package found — audio decode enabled")
    except ImportError:
        logger.critical(
            "PyAV (av) is required for audio decode. Run: pip install av"
        )
        sys.exit(1)

    # 5. edge-tts — check availability (primary TTS)
    try:
        import edge_tts as _  # noqa: F401

        logger.info("✓ edge-tts package found — TTS enabled")
    except ImportError:
        logger.warning(
            "⚠ edge-tts not installed — TTS will fall back to Google or fail. "
            "Run: pip install edge-tts"
        )

    if not errors:
        logger.info("✓ Voice service dependencies validated successfully.")


@app.on_event("shutdown")
async def shutdown():
    """Clean up resources on shutdown."""
    from app.services.voice import _voice_service

    if _voice_service is not None:
        await _voice_service.gateway.session.close()
        logger.info("Redis connection closed.")


@app.get("/health", tags=["Health"])
async def health_check():
    """Service health status endpoint."""
    return {
        "success": True,
        "message": "GigBridge AI Microservice is running.",
        "data": {
            "status": "healthy",
            "active_llm_provider": settings.DEFAULT_LLM_PROVIDER,
            "redis_configured": bool(settings.REDIS_URL),
            "google_creds_configured": bool(settings.GOOGLE_APPLICATION_CREDENTIALS),
            "stt_primary": settings.STT_PRIMARY_PROVIDER,
            "tts_primary": settings.TTS_PRIMARY_PROVIDER,
        },
        "errors": [],
    }
