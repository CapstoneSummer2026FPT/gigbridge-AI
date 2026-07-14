import logging
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.security import verify_api_key
from app.core.rate_limit import limiter, rate_limit_exceeded_handler
from app.api.routes import job_posts, interviews, matching, analysis, rag

logger = logging.getLogger("ai_server")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Validate dependencies and cleanly drain resources."""
    await validate_voice_dependencies()
    try:
        yield
    finally:
        await shutdown()

app = FastAPI(
    title="GigBridge AI Service",
    description="Stand-alone Microservice providing NLP and AI intelligence to GigBridge platform.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

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
app.include_router(
    rag.router,
    prefix="/api/ai",
    tags=["RAG Knowledge Base"],
    dependencies=[Depends(verify_api_key)]
)


async def validate_voice_dependencies():
    """Validate voice service dependencies at startup.

    Fails fast if Redis is unavailable (no session state = no interview flow).
    Warns if Google credentials are missing (STT/TTS fallback limited).
    Validates Faster-Whisper only if configured as active provider.
    """
    errors: list[str] = []
    redis_client = None

    # 1. Redis — fail fast (mandatory for all interview flows)
    try:
        redis_client = aioredis.from_url(settings.REDIS_URL)
        await redis_client.ping()
        server_info = await redis_client.info("server")
        version_text = str(server_info.get("redis_version", "0.0"))
        version_parts = version_text.split(".")
        redis_version = tuple(int(part) for part in version_parts[:2])
        if redis_version < (6, 2):
            raise RuntimeError(
                f"Redis 6.2+ is required for atomic GETDEL (found {version_text})"
            )
        logger.info("Redis connection OK (version %s)", version_text)
    except Exception as exc:
        errors.append(f"Redis unavailable: {exc}")
        logger.critical(
            "STARTUP FAILED: Redis is required for session state — %s", exc
        )
        raise RuntimeError("Redis 6.2+ is required for interview state") from exc
    finally:
        if redis_client is not None:
            await redis_client.aclose()

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
            raise RuntimeError("Configured Faster-Whisper dependency is missing")
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
        logger.info("Google credentials configured")

    # 4. PyAV — check availability (critical for audio decode)
    try:
        import av as _  # noqa: F401

        logger.info("✓ PyAV (av) package found — audio decode enabled")
    except ImportError:
        logger.critical(
            "PyAV (av) is required for audio decode. Run: pip install av"
        )
        raise RuntimeError("PyAV dependency is missing")

    # 5. edge-tts — optional TTS provider
    if settings.TTS_PRIMARY_PROVIDER == "edge_tts" or settings.TTS_FALLBACK_PROVIDER == "edge_tts":
        try:
            import edge_tts as _  # noqa: F401

            logger.info("✓ edge-tts package found — TTS enabled")
        except ImportError:
            logger.warning(
                "⚠ edge-tts is configured but not installed. "
                "Run: pip install edge-tts"
            )

    # 6. ElevenLabs — optional paid TTS provider
    if settings.TTS_PRIMARY_PROVIDER == "elevenlabs" or settings.TTS_FALLBACK_PROVIDER == "elevenlabs":
        if settings.ELEVENLABS_API_KEY:
            logger.info("✓ ELEVENLABS_API_KEY configured — ElevenLabs TTS enabled")
        else:
            logger.warning(
                "⚠ ElevenLabs TTS is configured but ELEVENLABS_API_KEY is not set. "
                "TTS will fall back to the next configured provider."
            )

    # 7. VieNeu — optional local Vietnamese/English testing TTS
    if settings.TTS_PRIMARY_PROVIDER == "vieneu" or settings.TTS_FALLBACK_PROVIDER == "vieneu":
        if settings.HF_TOKEN:
            logger.info("✓ HF_TOKEN configured — Hugging Face Hub requests will be authenticated")
        else:
            logger.warning(
                "⚠ HF_TOKEN not set — Hugging Face Hub downloads may be rate-limited. "
                "Set HF_TOKEN in .env to authenticate model downloads."
            )
        try:
            import vieneu as _  # noqa: F401

            logger.info("✓ VieNeu package found — local TTS enabled")
        except ImportError:
            logger.warning(
                "⚠ VieNeu TTS is configured but not installed. "
                "Run: pip install vieneu"
            )

    if not errors:
        logger.info("✓ Voice service dependencies validated successfully.")


async def shutdown():
    """Clean up resources on shutdown."""
    from app.services.voice import _voice_service
    from app.services.interviews import _interview_service

    if _interview_service is not None:
        await _interview_service.shutdown()

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
