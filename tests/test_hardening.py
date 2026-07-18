"""Security and reliability regression tests for the AI interview service."""

import asyncio
import hashlib
import sys
import threading
import types
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError
from starlette.requests import Request


def test_production_rejects_missing_and_placeholder_api_keys():
    from app.core.config import Settings

    for value in ("", "dev-key-please-change-in-env", "your-secure-shared-api-key-here"):
        with pytest.raises(ValidationError):
            Settings(APP_ENV="production", AI_SERVER_API_KEY=value, _env_file=None)


def test_explicit_test_environment_allows_development_key():
    from app.core.config import Settings

    configured = Settings(
        APP_ENV="test",
        AI_SERVER_API_KEY="dev-key-please-change-in-env",
        _env_file=None,
    )
    assert configured.APP_ENV == "test"


def test_api_key_verification_uses_constant_time_comparison():
    from app.core.config import settings
    from app.core.security import verify_api_key

    with (
        patch.object(settings, "AI_SERVER_API_KEY", "expected"),
        patch("app.core.security.secrets.compare_digest", return_value=True) as compare,
    ):
        assert asyncio.run(verify_api_key("provided")) == "provided"
    compare.assert_called_once_with("provided", "expected")


def test_schema_constraints_and_session_id_validation():
    from app.api.schemas.interviews import (
        ConfirmAnswerRequest,
        DraftDataResponse,
        InterviewFeedback,
        StartInterviewRequest,
        SubmitAnswerRequest,
    )

    base = {"job_id": "j", "freelancer_id": "f", "job_title": "Engineer"}
    with pytest.raises(ValidationError):
        StartInterviewRequest(**base, mode="video")
    with pytest.raises(ValidationError):
        StartInterviewRequest(**base, language="fr")
    with pytest.raises(ValidationError):
        InterviewFeedback(
            score=101,
            summary="x",
            technical_skills=[],
            soft_skills=[],
            recommended_hire=False,
        )
    with pytest.raises(ValidationError):
        DraftDataResponse(
            session_id="int_12345678",
            draft_id="draft_x",
            question_index=1,
            transcript="x",
            language="en",
            stt_provider="fake",
            confidence=1.1,
            expires_at="now",
        )

    for invalid in ("short", "bad session", "bad/path", "bad\r\nkey", "x" * 129):
        with pytest.raises(ValidationError):
            SubmitAnswerRequest(session_id=invalid, answer_text="answer")
    assert ConfirmAnswerRequest(
        session_id="int_12345678", corrected_text=" fixed "
    ).corrected_text == "fixed"
    with pytest.raises(ValidationError, match="answer_text_required"):
        ConfirmAnswerRequest(session_id="int_12345678", corrected_text="   ")


def test_rate_limit_bucket_hashes_api_key():
    from app.core.rate_limit import api_key_bucket

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/",
        "headers": [(b"x-api-key", b"secret-value")],
        "client": ("127.0.0.1", 1234),
        "scheme": "http",
        "server": ("test", 80),
        "query_string": b"",
    }
    bucket = api_key_bucket(Request(scope))
    assert bucket == hashlib.sha256(b"secret-value").hexdigest()
    assert "secret-value" not in bucket


@pytest.mark.parametrize(
    ("setting_name", "allowed"),
    [
        ("RATE_LIMIT_START", 30),
        ("RATE_LIMIT_SUBMIT", 60),
        ("RATE_LIMIT_CONFIRM", 60),
        ("RATE_LIMIT_TRANSCRIBE", 30),
    ],
)
def test_configured_rate_limits_and_429_envelope(setting_name, allowed):
    from fastapi import FastAPI, Request as FastAPIRequest, Response
    from fastapi.testclient import TestClient
    from slowapi import Limiter
    from slowapi.errors import RateLimitExceeded

    from app.core.config import settings
    from app.core.rate_limit import api_key_bucket, rate_limit_exceeded_handler

    local_limiter = Limiter(
        key_func=api_key_bucket,
        storage_uri="memory://",
        headers_enabled=True,
    )
    app = FastAPI()
    app.state.limiter = local_limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

    @app.get("/paid")
    @local_limiter.limit(getattr(settings, setting_name))
    async def paid(request: FastAPIRequest, response: Response):
        return {"ok": True}

    client = TestClient(app)
    headers = {"X-API-Key": f"key-{setting_name}"}
    for _ in range(allowed):
        assert client.get("/paid", headers=headers).status_code == 200
    rejected = client.get("/paid", headers=headers)
    assert rejected.status_code == 429
    assert rejected.json() == {
        "success": False,
        "message": "Rate limit exceeded",
        "data": None,
        "errors": [],
    }
    assert "retry-after" in rejected.headers


def test_cors_preflight_allows_wildcard_without_credentials():
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.testclient import TestClient

    app = FastAPI()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    response = TestClient(app).options(
        "/anything",
        headers={
            "Origin": "https://example.test",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "X-API-Key",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "*"
    assert "access-control-allow-credentials" not in response.headers


def test_session_id_constraint_applies_to_form_and_path_routes():
    from fastapi import FastAPI, Form, Path as FastAPIPath
    from fastapi.testclient import TestClient

    from app.api.schemas.interviews import SESSION_ID_PATTERN

    app = FastAPI()

    @app.post("/form")
    async def form_route(
        session_id: str = Form(
            ..., min_length=8, max_length=128, pattern=SESSION_ID_PATTERN
        )
    ):
        return {"session_id": session_id}

    @app.get("/path/{session_id}")
    async def path_route(
        session_id: str = FastAPIPath(
            ..., min_length=8, max_length=128, pattern=SESSION_ID_PATTERN
        )
    ):
        return {"session_id": session_id}

    client = TestClient(app)
    assert client.post("/form", data={"session_id": "bad session"}).status_code == 422
    assert client.get("/path/short").status_code == 422
    assert client.post("/form", data={"session_id": "int_12345678"}).status_code == 200


def test_exception_handlers_hide_internal_and_provider_details():
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.core.exceptions import VoiceProviderException, register_exception_handlers

    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/internal")
    async def internal():
        raise RuntimeError("C:/secret/provider/path")

    @app.get("/provider")
    async def provider():
        raise VoiceProviderException(
            "credential leaked", errors=["provider stack detail"]
        )

    client = TestClient(app, raise_server_exceptions=False)
    internal_response = client.get("/internal")
    provider_response = client.get("/provider")
    assert internal_response.status_code == 500
    assert "secret" not in internal_response.text
    assert internal_response.json()["errors"] == []
    assert provider_response.status_code == 503
    assert "credential" not in provider_response.text
    assert "provider stack" not in provider_response.text


class _FakeRedis:
    def __init__(self):
        self.hashes = {}
        self.expirations = []

    async def hset(self, key, mapping):
        self.hashes[key] = dict(mapping)

    async def expire(self, key, ttl):
        self.expirations.append((key, ttl))

    async def hgetall(self, key):
        return self.hashes.get(key, {})

    async def hget(self, key, field):
        return self.hashes.get(key, {}).get(field)


def test_session_creation_validates_job_id_and_uses_text_default():
    from app.clients.voice.session import VoiceSessionManager
    from app.core.exceptions import InvalidSessionDataError

    manager = VoiceSessionManager()
    manager._redis = _FakeRedis()
    with pytest.raises(InvalidSessionDataError):
        asyncio.run(manager.create_session({}))

    session = asyncio.run(manager.create_session({"job_id": "job-1"}))
    assert session.mode == "text"
    assert session.stt_language == "vi"


def test_native_getdel_failure_is_never_degraded():
    from app.clients.voice.session import VoiceSessionManager

    class BrokenRedis:
        async def getdel(self, key):
            raise ConnectionError("redis down")

    manager = VoiceSessionManager()
    manager._redis = BrokenRedis()
    with pytest.raises(ConnectionError):
        asyncio.run(manager._atomic_getdel("draft:int_12345678"))


def test_concurrent_draft_consumers_only_receive_one_value():
    import json

    from app.clients.voice.session import VoiceSessionManager

    class AtomicRedis:
        def __init__(self):
            self.value = json.dumps(
                {
                    "draft_id": "draft_test",
                    "question_index": 1,
                    "transcript": "answer",
                    "language": "en",
                    "stt_provider": "fake",
                    "confidence": 1.0,
                    "created_at": "now",
                }
            )
            self.lock = asyncio.Lock()

        async def getdel(self, key):
            async with self.lock:
                value, self.value = self.value, None
                return value

    async def consume_twice():
        manager = VoiceSessionManager()
        manager._redis = AtomicRedis()
        return await asyncio.gather(
            manager.consume_draft("int_12345678"),
            manager.consume_draft("int_12345678"),
        )

    results = asyncio.run(consume_twice())
    assert sum(result is not None for result in results) == 1


def test_audio_access_token_is_constant_time_hash_check():
    from app.clients.voice.session import VoiceSessionManager

    token = "a" * 43
    fake = _FakeRedis()
    fake.hashes["session:int_12345678"] = {
        "audio_access_token_hash": hashlib.sha256(token.encode()).hexdigest()
    }
    manager = VoiceSessionManager()
    manager._redis = fake
    assert asyncio.run(manager.verify_audio_access_token("int_12345678", token))
    assert not asyncio.run(
        manager.verify_audio_access_token("int_12345678", "b" * 43)
    )


def test_tts_cache_uses_one_binary_pipeline_with_expiry():
    from app.clients.voice.session import VoiceSessionManager
    from app.core.config import settings

    class Pipeline:
        def __init__(self):
            self.commands = []
            self.executions = 0

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        def set(self, key, value, ex=None):
            self.commands.append((key, value, ex))
            return self

        async def execute(self):
            self.executions += 1

    class BinaryRedis:
        def __init__(self):
            self.pipe = Pipeline()

        def pipeline(self, transaction=True):
            assert transaction is True
            return self.pipe

    binary = BinaryRedis()
    manager = VoiceSessionManager()
    manager._binary_redis = binary
    asyncio.run(manager.cache_tts("int_12345678", 1, b"raw-audio"))
    assert binary.pipe.executions == 1
    assert len(binary.pipe.commands) == 2
    assert binary.pipe.commands[0][1] == b"raw-audio"
    assert all(command[2] == settings.REDIS_TTS_CACHE_TTL for command in binary.pipe.commands)


def test_whisper_model_constructs_once_off_event_loop():
    from app.clients.voice.stt_engine.faster_whisper import FasterWhisperEngine

    calls = []

    class FakeWhisperModel:
        def __init__(self, *args, **kwargs):
            calls.append(threading.get_ident())

    async def run():
        loop_thread = threading.get_ident()
        engine = FasterWhisperEngine()
        with patch.dict(
            sys.modules,
            {"faster_whisper": types.SimpleNamespace(WhisperModel=FakeWhisperModel)},
        ):
            first, second = await asyncio.gather(
                engine._get_model(), engine._get_model()
            )
        return loop_thread, first, second

    loop_thread, first, second = asyncio.run(run())
    assert first is second
    assert len(calls) == 1
    assert calls[0] != loop_thread


def test_whisper_model_load_survives_caller_timeout():
    import time

    from app.clients.voice.stt_engine.faster_whisper import FasterWhisperEngine

    calls = []

    class SlowWhisperModel:
        def __init__(self, *args, **kwargs):
            calls.append(1)
            time.sleep(0.05)

    async def run():
        engine = FasterWhisperEngine()
        with patch.dict(
            sys.modules,
            {"faster_whisper": types.SimpleNamespace(WhisperModel=SlowWhisperModel)},
        ):
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(engine._get_model(), timeout=0.005)
            await asyncio.sleep(0.08)
            model = await engine._get_model()
        return model

    assert asyncio.run(run()) is not None
    assert len(calls) == 1


def test_whisper_auto_mode_passes_no_language_hint():
    from app.clients.voice.stt_engine.faster_whisper import FasterWhisperEngine

    engine = FasterWhisperEngine()
    engine._get_model = AsyncMock(return_value=object())
    engine._chunker = MagicMock()
    engine._chunker.split_wav.return_value = [types.SimpleNamespace(wav_bytes=b"wav")]
    engine._transcribe_wav_bytes = AsyncMock(
        return_value=("answer", [-0.1], "en")
    )
    result = asyncio.run(
        engine.transcribe(b"wav", "auto", primary_language="vi")
    )
    assert engine._transcribe_wav_bytes.await_args.kwargs["language"] is None
    assert result.language == "en"


def test_gateway_falls_back_on_unexpected_provider_exception():
    from app.clients.voice.gateway import VoiceGateway
    from app.clients.voice.models import TranscriptionResult

    class Broken:
        async def transcribe(self, *args):
            raise ValueError("bug")

    class Working:
        async def transcribe(self, *args):
            return TranscriptionResult("ok", "en", 1.0, "working")

    gateway = VoiceGateway.__new__(VoiceGateway)
    gateway.stt_providers = [("broken", Broken()), ("working", Working())]
    result = asyncio.run(gateway.transcribe_with_fallback(b"wav", "auto"))
    assert result.text == "ok"
    assert result.fallback_used is True


def test_tts_gateway_falls_back_on_unexpected_provider_exception():
    from app.clients.voice.gateway import VoiceGateway
    from app.clients.voice.models import SynthesisResult

    class Broken:
        async def synthesize(self, *args):
            raise ValueError("bug")

    class Working:
        async def synthesize(self, *args):
            return SynthesisResult(b"audio", "audio/mpeg", "working")

    gateway = VoiceGateway.__new__(VoiceGateway)
    gateway.tts_providers = [("broken", Broken()), ("working", Working())]
    result = asyncio.run(gateway._synthesize_segment_with_fallback("hello", "en"))
    assert result.audio_bytes == b"audio"
    assert result.fallback_used is True


def test_google_stt_rejects_result_without_alternatives():
    from app.clients.voice.stt_engine.google_stt import GoogleSTTEngine
    from app.core.exceptions import VoiceProviderException

    class RecognitionConfig:
        class AudioEncoding:
            LINEAR16 = "linear16"

        def __init__(self, **kwargs):
            pass

    class RecognitionAudio:
        def __init__(self, **kwargs):
            pass

    class SpeechContext:
        def __init__(self, **kwargs):
            pass

    speech_module = types.SimpleNamespace(
        RecognitionConfig=RecognitionConfig,
        RecognitionAudio=RecognitionAudio,
        SpeechContext=SpeechContext,
    )
    client = MagicMock()
    client.recognize = AsyncMock(
        return_value=types.SimpleNamespace(
            results=[types.SimpleNamespace(alternatives=[])]
        )
    )
    engine = GoogleSTTEngine()
    engine._get_client = AsyncMock(return_value=client)
    with patch.dict(sys.modules, {"google.cloud.speech": speech_module}):
        with pytest.raises(VoiceProviderException, match="empty results"):
            asyncio.run(engine.transcribe(b"wav", "en"))


def _import_interview_service():
    sys.modules.setdefault(
        "openai", types.SimpleNamespace(AsyncOpenAI=MagicMock())
    )
    from app.services.interviews import InterviewService

    return InterviewService


def test_blank_corrected_answer_is_rejected_before_draft_consumption():
    InterviewService = _import_interview_service()
    voice = MagicMock()
    voice.consume_draft = AsyncMock()
    service = InterviewService(llm_gateway=MagicMock(), voice_service=voice)
    from app.core.exceptions import InvalidAnswerError

    with pytest.raises(InvalidAnswerError):
        asyncio.run(service.confirm_answer("int_12345678", "   "))
    voice.consume_draft.assert_not_awaited()


def test_transcribe_preserves_auto_mode_and_reports_real_expiry():
    InterviewService = _import_interview_service()
    from app.clients.voice.models import TranscriptionResult
    from app.core.config import settings

    session = types.SimpleNamespace(
        question_index=1,
        language="vi",
        stt_language="auto",
        hotwords=[],
        job_phonetic_aliases={},
    )
    voice = MagicMock()
    voice.load_session = AsyncMock(return_value=session)
    voice.speech_to_text = AsyncMock(
        return_value=TranscriptionResult("answer", "en", 0.9, "fake")
    )
    voice.save_draft = AsyncMock()
    service = InterviewService(llm_gateway=MagicMock(), voice_service=voice)
    before = datetime.now(timezone.utc)
    response = asyncio.run(service.transcribe_audio("int_12345678", b"wav"))
    after = datetime.now(timezone.utc)

    assert voice.speech_to_text.await_args.args[1] == "auto"
    expiry = datetime.fromisoformat(response.expires_at)
    assert before.timestamp() + settings.REDIS_DRAFT_TTL <= expiry.timestamp()
    assert expiry.timestamp() <= after.timestamp() + settings.REDIS_DRAFT_TTL


def test_hotword_heuristic_rejects_numeric_ranges_and_all_caps_noise():
    InterviewService = _import_interview_service()
    hotwords = InterviewService._build_hotwords(
        "Backend Engineer",
        ["PostgreSQL"],
        "ERROR 12.5 3-5 node.js camelCase ordinary words",
    )
    assert "node.js" in hotwords
    assert "camelCase" in hotwords
    assert "ERROR" not in hotwords
    assert "12.5" not in hotwords
    assert "3-5" not in hotwords


def test_malformed_feedback_degrades_to_safe_result():
    InterviewService = _import_interview_service()
    llm = MagicMock()
    llm.generate = AsyncMock(return_value="not json")
    voice = MagicMock()
    voice.get_history = AsyncMock(return_value=[])
    service = InterviewService(llm_gateway=llm, voice_service=voice)
    feedback = asyncio.run(service._generate_feedback("int_12345678"))
    assert feedback.score == 0
    assert feedback.recommended_hire is False


def test_background_tts_task_is_retained_and_cleaned_up():
    InterviewService = _import_interview_service()

    async def run():
        release = asyncio.Event()
        voice = MagicMock()
        voice.get_cached_tts = AsyncMock(return_value=None)
        voice.get_tts_status = AsyncMock(return_value={"status": "missing"})
        voice.set_tts_status = AsyncMock()
        service = InterviewService(llm_gateway=MagicMock(), voice_service=voice)

        async def background(*args, **kwargs):
            await release.wait()

        service._generate_question_tts_background = background
        await service.schedule_question_tts("int_12345678", 1, "Question", "en")
        assert len(service._pending_tts_tasks) == 1
        release.set()
        await asyncio.gather(*list(service._pending_tts_tasks))
        await asyncio.sleep(0)
        assert not service._pending_tts_tasks

    asyncio.run(run())


def test_background_tts_failure_stores_only_generic_error():
    InterviewService = _import_interview_service()

    async def run():
        voice = MagicMock()
        voice.set_tts_status = AsyncMock()
        voice.text_to_speech = AsyncMock(
            side_effect=RuntimeError("C:/provider/private/path")
        )
        service = InterviewService(llm_gateway=MagicMock(), voice_service=voice)
        await service._generate_question_tts_background(
            "int_12345678", 1, "Question", "en"
        )
        failed_call = voice.set_tts_status.await_args_list[-1]
        assert failed_call.args == (
            "int_12345678",
            1,
            "failed",
            "tts_generation_failed",
        )

    asyncio.run(run())


def test_lifespan_and_safe_logging_are_present():
    source = (Path(__file__).parents[1] / "app" / "main.py").read_text("utf-8")
    assert "@app.on_event" not in source
    assert "lifespan=lifespan" in source
    assert 'allow_credentials=False' in source
    assert 'settings.GOOGLE_APPLICATION_CREDENTIALS,' not in source
    assert 'logger.info("✓ Redis connection OK (%s)", settings.REDIS_URL)' not in source


@pytest.mark.parametrize(
    ("redis_version", "should_pass"),
    [("6.1.9", False), ("6.2.0", True), ("7.4.1", True)],
)
def test_startup_requires_redis_6_2_or_newer(redis_version, should_pass):
    from app import main
    from app.core.config import settings

    class FakeRedis:
        closed = False

        async def ping(self):
            return True

        async def info(self, section):
            assert section == "server"
            return {"redis_version": redis_version}

        async def aclose(self):
            self.closed = True

    fake_redis = FakeRedis()
    with (
        patch("app.main.aioredis.from_url", return_value=fake_redis),
        patch.object(settings, "STT_PRIMARY_PROVIDER", "google"),
        patch.object(settings, "STT_FALLBACK_PROVIDER", "google"),
        patch.object(settings, "TTS_PRIMARY_PROVIDER", "google"),
        patch.object(settings, "TTS_FALLBACK_PROVIDER", "google"),
    ):
        if should_pass:
            asyncio.run(main.validate_voice_dependencies())
        else:
            with pytest.raises(RuntimeError, match="Redis 6.2"):
                asyncio.run(main.validate_voice_dependencies())
    assert fake_redis.closed is True


def test_predefined_job_questions_flow():
    InterviewService = _import_interview_service()
    import json
    from app.api.schemas.interviews import StartInterviewRequest
    from app.clients.voice.models import InterviewSession, DraftData

    # Mock Voice Service
    voice = MagicMock()
    
    session = InterviewSession(
        session_id="int_12345678",
        job_id="job_abc",
        freelancer_id="free_xyz",
        mode="text",
        language="en",
        question_index=1,
        job_questions=["Q1", "Q2"]
    )
    voice.create_session = AsyncMock(return_value=session)
    voice.add_history = AsyncMock()
    
    # Mock LLM Gateway (should not be called for question generation)
    llm = MagicMock()
    llm.generate = AsyncMock()

    service = InterviewService(llm_gateway=llm, voice_service=voice)
    
    # 1. Initialize
    request = StartInterviewRequest(
        job_id="job_abc",
        freelancer_id="free_xyz",
        job_title="Engineer",
        job_questions=["Q1", "Q2"]
    )
    response = asyncio.run(service.initialize_interview(request))
    assert response.question_text == "Q1"
    assert response.question_index == 1
    assert response.job_id == "job_abc"
    assert response.freelancer_id == "free_xyz"
    llm.generate.assert_not_called()

    # 2. Confirm first answer, should get Q2
    voice.load_session = AsyncMock(return_value=session)
    draft = DraftData(
        draft_id="draft_123",
        question_index=1,
        transcript="Answer 1",
        language="en",
        stt_provider="test",
        confidence=1.0,
        created_at="now"
    )
    voice.consume_draft = AsyncMock(return_value=draft)
    voice.mark_confirmed = AsyncMock()
    voice.get_history = AsyncMock(return_value=[])
    voice.advance_pointer = AsyncMock()

    response2 = asyncio.run(service.confirm_answer("int_12345678", "Answer 1"))
    assert response2.is_completed is False
    assert response2.question_text == "Q2"
    assert response2.question_index == 2
    assert response2.job_id == "job_abc"
    assert response2.freelancer_id == "free_xyz"
    llm.generate.assert_not_called()

    # 3. Confirm second answer, should finish interview
    session.question_index = 2
    draft.question_index = 2
    draft.transcript = "Answer 2"
    
    # Mock feedback generation LLM response
    llm.generate = AsyncMock(return_value="not json")

    response3 = asyncio.run(service.confirm_answer("int_12345678", "Answer 2"))
    assert response3.is_completed is True
    assert response3.feedback is not None
    assert response3.feedback.score == 0
    assert response3.job_id == "job_abc"
    assert response3.freelancer_id == "free_xyz"

