"""Unit tests for the Voice Interview MVP — no external services required.

Tests cover:
  - Models: dataclass construction, Language enum, VoiceErrorCode
  - AudioProcessor: upload validation, silence detection, WAV building
  - Session: draft serialization (without Redis)
  - Exceptions: hierarchy and error codes
  - Base engines: contract enforcement (abstract methods)
"""

import asyncio
import io
import json
import sys
import struct
import types
import wave
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ═══════════════════════════════════════════════════════════════
# Models
# ═══════════════════════════════════════════════════════════════

class TestModels:
    def test_transcription_result_creation(self):
        from app.clients.voice.models import TranscriptionResult
        r = TranscriptionResult(
            text="Xin chào",
            language="vi",
            confidence=0.95,
            stt_provider="google_stt",
            fallback_used=False,
        )
        assert r.text == "Xin chào"
        assert r.confidence == 0.95
        assert r.stt_provider == "google_stt"
        assert r.fallback_used is False

    def test_synthesis_result_creation(self):
        from app.clients.voice.models import SynthesisResult
        r = SynthesisResult(
            audio_bytes=b"fake_mp3_data",
            mime_type="audio/mpeg",
            tts_provider="edge_tts",
            fallback_used=False,
        )
        assert len(r.audio_bytes) == 13
        assert r.mime_type == "audio/mpeg"

    def test_draft_data_creation(self):
        from app.clients.voice.models import DraftData
        d = DraftData(
            draft_id="draft_abc123",
            question_index=2,
            transcript="Tôi có kinh nghiệm React",
            language="vi",
            stt_provider="google_stt",
            confidence=0.94,
            created_at="2026-06-18T12:20:00Z",
        )
        assert d.question_index == 2
        assert d.confirmed is False  # default

    def test_interview_session_creation(self):
        from app.clients.voice.models import InterviewSession
        s = InterviewSession(
            session_id="int_abc123",
            job_id="j1",
            freelancer_id="f1",
            mode="voice",
            language="vi",
            question_index=1,
        )
        assert s.mode == "voice"
        assert s.question_index == 1

    def test_language_enum_parse(self):
        from app.clients.voice.models import Language
        assert Language.parse("vi") == Language.VIETNAMESE
        assert Language.parse("vi-VN") == Language.VIETNAMESE
        assert Language.parse("en") == Language.ENGLISH
        assert Language.parse("en-US") == Language.ENGLISH
        assert Language.parse("vi_vn") == Language.VIETNAMESE
        assert Language.parse("") == Language.VIETNAMESE  # default
        assert Language.parse(None) == Language.VIETNAMESE  # None → default
        with pytest.raises(ValueError):
            Language.parse("fr")

    def test_language_tts_code(self):
        from app.clients.voice.models import Language
        assert Language.VIETNAMESE.tts_code() == "vi-VN"
        assert Language.ENGLISH.tts_code() == "en-US"

    def test_language_stt_hint(self):
        from app.clients.voice.models import Language
        assert Language.VIETNAMESE.stt_hint() == "vi"
        assert Language.ENGLISH.stt_hint() == "en"

    def test_voice_error_code_stability(self):
        from app.clients.voice.models import VoiceErrorCode
        # These codes are part of the frontend contract — never rename
        assert VoiceErrorCode.SESSION_NOT_FOUND.value == "session_not_found"
        assert VoiceErrorCode.DRAFT_EXPIRED.value == "draft_expired"
        assert VoiceErrorCode.NO_SPEECH_DETECTED.value == "no_speech_detected"
        assert VoiceErrorCode.UPLOAD_TOO_LARGE.value == "upload_too_large"
        assert VoiceErrorCode.UNSUPPORTED_AUDIO_TYPE.value == "unsupported_audio_type"
        assert VoiceErrorCode.PROVIDER_UNAVAILABLE.value == "provider_unavailable"
        assert VoiceErrorCode.CONFIRM_CONFLICT.value == "confirm_conflict"
        assert VoiceErrorCode.DRAFT_INDEX_MISMATCH.value == "draft_index_mismatch"


# ═══════════════════════════════════════════════════════════════
# Exceptions
# ═══════════════════════════════════════════════════════════════

class TestExceptions:
    def test_voice_provider_exception(self):
        from app.core.exceptions import VoiceProviderException
        exc = VoiceProviderException("Google STT failed")
        assert exc.status_code == 503
        assert "Google" in str(exc)

    def test_audio_validation_error(self):
        from app.core.exceptions import AudioValidationError
        exc = AudioValidationError("no_speech_detected", 400)
        assert exc.status_code == 400
        assert exc.error_code == "no_speech_detected"

    def test_session_expired_error(self):
        from app.core.exceptions import SessionExpiredError
        exc = SessionExpiredError()
        assert exc.status_code == 401

    def test_draft_expired_error(self):
        from app.core.exceptions import DraftExpiredError
        exc = DraftExpiredError()
        assert exc.status_code == 410

    def test_confirm_conflict_error(self):
        from app.core.exceptions import ConfirmConflictError
        exc = ConfirmConflictError()
        assert exc.status_code == 409


# ═══════════════════════════════════════════════════════════════
# Config
# ═══════════════════════════════════════════════════════════════

class TestConfig:
    def test_default_stt_provider_is_faster_whisper(self):
        """Faster-Whisper is the cheap local/testing primary provider."""
        from app.core.config import settings
        assert settings.STT_PRIMARY_PROVIDER == "faster_whisper"

    def test_default_tts_provider_is_edge_tts(self):
        from app.core.config import settings
        assert settings.TTS_PRIMARY_PROVIDER == "edge_tts"

    def test_google_tts_requires_credentials_at_init(self):
        from app.clients.voice.tts_engine.google_tts import GoogleTTSEngine
        from app.core.config import settings
        from app.core.exceptions import VoiceProviderException

        with patch.object(settings, "GOOGLE_APPLICATION_CREDENTIALS", ""):
            with pytest.raises(VoiceProviderException, match="GOOGLE_APPLICATION_CREDENTIALS"):
                GoogleTTSEngine()

    def test_redis_url_default(self):
        from app.core.config import settings
        assert "redis://" in settings.REDIS_URL

    def test_audio_limits_reasonable(self):
        from app.core.config import settings
        assert settings.AUDIO_MAX_SIZE_BYTES == 3_145_728  # 3MB
        assert settings.AUDIO_MAX_DURATION_SECONDS == 90
        assert 0 < settings.AUDIO_SILENCE_THRESHOLD < 1.0

    def test_max_interview_questions(self):
        from app.core.config import settings
        assert settings.MAX_INTERVIEW_QUESTIONS == 3


# ═══════════════════════════════════════════════════════════════
# Transcript correction
# ═══════════════════════════════════════════════════════════════

class TestTranscriptCorrection:
    def test_phonetic_matcher_uses_lookup_only_with_hotword_gate(self):
        from app.services.phonetic_matcher import PhoneticMatcher

        matcher = PhoneticMatcher({"phich ma": "Figma"})
        assert matcher.correct("toi dung phich ma", ["Figma"]) == "toi dung Figma"
        assert matcher.correct("toi dung phich ma", ["React"]) == "toi dung phich ma"
        backend = PhoneticMatcher({"bat kenh": "backend"})
        assert backend.correct("toi lam bat kenh", ["Backend Developer"]) == "toi lam backend"

    def test_phonetic_matcher_generates_aliases_from_current_hotwords(self):
        from app.services.phonetic_matcher import PhoneticMatcher

        matcher = PhoneticMatcher()
        assert matcher.correct("toi lam back kenh", ["backend"]) == "toi lam backend"
        assert matcher.correct("toi lam back kenh", ["Sales"]) == "toi lam back kenh"

    def test_phonetic_matcher_accepts_job_scoped_aliases(self):
        from app.services.phonetic_matcher import PhoneticMatcher

        matcher = PhoneticMatcher()
        aliases = {"backend": ["bat kenh"]}
        assert matcher.correct("toi lam bat kenh", ["backend"], aliases) == "toi lam backend"
        assert matcher.correct("toi lam bat kenh", ["Sales"], aliases) == "toi lam bat kenh"

    def test_phonetic_matcher_does_not_escape_job_zone(self):
        from app.services.phonetic_matcher import PhoneticMatcher

        matcher = PhoneticMatcher(
            {
                "Sales": ["seu", "seo"],
                "Software Engineer": ["soft engineer"],
            }
        )
        assert matcher.correct("toi lam seu", ["Software Engineer"]) == "toi lam seu"
        assert matcher.correct("toi lam seu", ["Sales"]) == "toi lam Sales"

    def test_typo_matcher_corrects_hotword_typos(self):
        from app.services.typo_matcher import TypoMatcher

        matcher = TypoMatcher(min_score=80)
        result = matcher.correct("I used Recat and TypeScript", ["React", "TypeScript"])
        assert result == "I used React and TypeScript"

    def test_transcript_corrector_returns_single_corrected_text(self):
        from app.services.phonetic_matcher import PhoneticMatcher
        from app.services.transcript_corrector import TranscriptCorrector
        from app.services.typo_matcher import TypoMatcher

        corrector = TranscriptCorrector(
            phonetic_matcher=PhoneticMatcher({"phich ma": "Figma"}),
            typo_matcher=TypoMatcher(min_score=80),
        )
        result = corrector.correct("toi dung phich ma va Recat", ["Figma", "React"])
        assert result.corrected_text == "toi dung Figma va React"
        assert result.changed is True

    def test_transcript_corrector_uses_job_scoped_phonetic_aliases(self):
        from app.services.transcript_corrector import TranscriptCorrector

        corrector = TranscriptCorrector()
        result = corrector.correct(
            "toi lam bat kenh",
            ["backend"],
            phonetic_aliases={"backend": ["bat kenh"]},
        )
        assert result.corrected_text == "toi lam backend"


class TestTTSSegmentRouter:
    def test_routes_english_hotword_inside_vietnamese_sentence(self):
        from app.services.tts_segment_router import TTSSegmentRouter

        router = TTSSegmentRouter()
        segments = router.route(
            "Hay giai thich React trong du an cua ban.",
            "vi",
            hotwords=["React"],
        )

        assert [(segment.text, segment.language) for segment in segments] == [
            ("Hay giai thich ", "vi"),
            ("React", "en"),
            (" trong du an cua ban.", "vi"),
        ]

    def test_detects_english_sentence_for_rest_of_text(self):
        from app.services.tts_segment_router import TTSSegmentRouter

        router = TTSSegmentRouter()
        segments = router.route(
            "What did you build with Docker? Hay noi ngan gon.",
            "vi",
            hotwords=[],
        )

        assert [(segment.text, segment.language) for segment in segments] == [
            ("What did you build with Docker?", "en"),
            (" Hay noi ngan gon.", "vi"),
        ]

    def test_merges_adjacent_same_voice_segments(self):
        from app.services.tts_segment_router import TTSSegmentRouter

        router = TTSSegmentRouter()
        segments = router.route(
            "What did you build? Which API did you use?",
            "vi",
            hotwords=[],
        )

        assert len(segments) == 1
        assert segments[0].language == "en"


class TestBilingualTTSSynthesis:
    @staticmethod
    def _wav_bytes(amplitude: int, samples: int = 2400, sample_rate: int = 24000):
        data = (np.ones(samples, dtype=np.int16) * amplitude).tobytes()
        output = io.BytesIO()
        with wave.open(output, "wb") as writer:
            writer.setnchannels(1)
            writer.setsampwidth(2)
            writer.setframerate(sample_rate)
            writer.writeframes(data)
        return output.getvalue()

    def test_gateway_uses_one_voice_for_complete_question(self):
        from app.clients.voice.gateway import VoiceGateway
        from app.clients.voice.models import SynthesisResult

        class FakeTTS:
            def __init__(self):
                self.calls = []

            async def synthesize(self, text: str, language: str):
                self.calls.append((text, language))
                return SynthesisResult(
                    audio_bytes=TestBilingualTTSSynthesis._wav_bytes(1000),
                    mime_type="audio/wav",
                    tts_provider="fake",
                )

        fake_tts = FakeTTS()
        gateway = VoiceGateway.__new__(VoiceGateway)
        gateway.tts_providers = [("fake", fake_tts)]

        result = asyncio.run(
            gateway.synthesize_with_fallback(
                "Hay dung React.",
                "vi",
                hotwords=["React"],
            )
        )

        assert fake_tts.calls == [("Hay dung React.", "vi")]
        assert result.audio_bytes.startswith(b"RIFF")
        assert result.mime_type == "audio/wav"
        assert result.tts_provider == "fake"

    def test_edge_tts_yields_audio_frames_without_buffering(self):
        from app.clients.voice.tts_engine.edge_tts_engine import EdgeTTSEngine

        class FakeCommunicate:
            def __init__(self, text, voice):
                assert text == "Hay mo ta React trong du an cua ban."
                assert voice

            async def stream(self):
                yield {"type": "audio", "data": b"first-frame"}
                yield {"type": "WordBoundary", "data": b""}
                yield {"type": "audio", "data": b"second-frame"}

        async def collect():
            engine = EdgeTTSEngine()
            return [
                chunk
                async for chunk in engine.stream_synthesize(
                    "Hay mo ta React trong du an cua ban.", "vi"
                )
            ]

        with patch(
            "app.clients.voice.tts_engine.edge_tts_engine.edge_tts.Communicate",
            FakeCommunicate,
        ):
            chunks = asyncio.run(collect())

        assert chunks == [b"first-frame", b"second-frame"]


class TestVieNeuTTSEngine:
    def test_vieneu_requires_optional_sdk(self):
        from app.clients.voice.tts_engine.vieneu_tts import VieNeuTTSEngine
        from app.core.exceptions import VoiceProviderException

        with patch.dict(sys.modules, {"vieneu": None}):
            with pytest.raises(VoiceProviderException, match="pip install vieneu"):
                VieNeuTTSEngine()

    def test_vieneu_synthesizes_numpy_audio_as_wav(self):
        from app.clients.voice.tts_engine.vieneu_tts import VieNeuTTSEngine

        class FakeVieneu:
            def infer(self, text: str):
                assert text == "Xin chao React"
                return np.ones(2400, dtype=np.float32) * 0.25

        fake_module = types.SimpleNamespace(Vieneu=FakeVieneu)
        with patch.dict(sys.modules, {"vieneu": fake_module}):
            engine = VieNeuTTSEngine()
            result = asyncio.run(engine.synthesize("Xin chao React", "vi"))

        assert result.audio_bytes.startswith(b"RIFF")
        assert result.mime_type == "audio/wav"
        assert result.tts_provider == "vieneu"


class TestElevenLabsTTSEngine:
    def test_elevenlabs_requires_api_key_at_init(self):
        from app.clients.voice.tts_engine.elevenlabs_tts import ElevenLabsTTSEngine
        from app.core.config import settings
        from app.core.exceptions import VoiceProviderException

        with patch.object(settings, "ELEVENLABS_API_KEY", ""):
            with pytest.raises(VoiceProviderException, match="ELEVENLABS_API_KEY"):
                ElevenLabsTTSEngine()

    def test_elevenlabs_synthesizes_mp3_audio(self):
        from app.clients.voice.tts_engine.elevenlabs_tts import ElevenLabsTTSEngine
        from app.core.config import settings

        calls = []

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def read(self):
                return b"mp3-data"

        def fake_urlopen(req, timeout):
            body = json.loads(req.data.decode("utf-8"))
            calls.append(
                {
                    "url": req.full_url,
                    "headers": dict(req.header_items()),
                    "json": body,
                    "timeout": timeout,
                }
            )
            return FakeResponse()

        with (
            patch.object(settings, "ELEVENLABS_API_KEY", "test-key"),
            patch.object(settings, "ELEVENLABS_MODEL", "eleven_multilingual_v2"),
            patch.object(settings, "ELEVENLABS_OUTPUT_FORMAT", "mp3_44100_128"),
            patch.object(settings, "ELEVENLABS_VOICE_ID", "default-voice"),
            patch.object(settings, "ELEVENLABS_VOICE_ID_EN", "english-voice"),
            patch("app.clients.voice.tts_engine.elevenlabs_tts.request.urlopen", fake_urlopen),
        ):
            engine = ElevenLabsTTSEngine()
            result = asyncio.run(engine.synthesize("Hello React", "en"))

        assert result.audio_bytes == b"mp3-data"
        assert result.mime_type == "audio/mpeg"
        assert result.tts_provider == "elevenlabs"
        assert calls[0]["url"].endswith(
            "/english-voice?output_format=mp3_44100_128"
        )
        assert calls[0]["headers"]["Xi-api-key"] == "test-key"
        assert calls[0]["json"] == {
            "text": "Hello React",
            "model_id": "eleven_multilingual_v2",
        }
        assert calls[0]["timeout"] == settings.TTS_PROVIDER_TIMEOUT


class TestTTSAudioStitcher:
    @staticmethod
    def _wav_bytes(samples: np.ndarray, sample_rate: int = 24000):
        output = io.BytesIO()
        with wave.open(output, "wb") as writer:
            writer.setnchannels(1)
            writer.setsampwidth(2)
            writer.setframerate(sample_rate)
            writer.writeframes(samples.astype(np.int16).tobytes())
        return output.getvalue()

    @staticmethod
    def _read_wav_samples(wav_bytes: bytes):
        with wave.open(io.BytesIO(wav_bytes), "rb") as reader:
            frames = reader.readframes(reader.getnframes())
        return np.frombuffer(frames, dtype=np.int16)

    def test_stitcher_crossfades_and_normalizes_wav_segments(self):
        from app.clients.voice.models import SynthesisResult
        from app.services.tts_audio_stitcher import TTSAudioStitcher

        segment_a = SynthesisResult(
            audio_bytes=self._wav_bytes(
                np.ones(1000, dtype=np.int16) * 1000,
                sample_rate=1000,
            ),
            mime_type="audio/wav",
            tts_provider="fake",
        )
        segment_b = SynthesisResult(
            audio_bytes=self._wav_bytes(
                np.ones(1000, dtype=np.int16) * 2000,
                sample_rate=1000,
            ),
            mime_type="audio/wav",
            tts_provider="fake",
        )

        stitched = TTSAudioStitcher(
            sample_rate=1000,
            crossfade_ms=100,
            peak=0.5,
        ).stitch([segment_a, segment_b])
        samples = self._read_wav_samples(stitched.audio_bytes)

        assert stitched.mime_type == "audio/wav"
        assert len(samples) == 1900
        assert np.max(np.abs(samples)) <= 16384

    def test_single_segment_returns_original_result(self):
        from app.clients.voice.models import SynthesisResult
        from app.services.tts_audio_stitcher import TTSAudioStitcher

        segment = SynthesisResult(
            audio_bytes=b"one",
            mime_type="audio/mpeg",
            tts_provider="fake",
        )

        assert TTSAudioStitcher().stitch([segment]) is segment


# ═══════════════════════════════════════════════════════════════
# AudioProcessor — validation only (no PyAV decode)
# ═══════════════════════════════════════════════════════════════

class TestAudioProcessorValidation:
    def setup_method(self):
        from app.services.audio_processor import AudioProcessor
        self.processor = AudioProcessor()

    def test_accepts_valid_content_type(self):
        size = self.processor.validate_request("audio/webm;codecs=opus", "1000")
        assert size == 1000

    def test_accepts_webm_without_codecs(self):
        size = self.processor.validate_request("audio/webm", "500")
        assert size == 500

    def test_accepts_wav(self):
        size = self.processor.validate_request("audio/wav", "2000")
        assert size == 2000

    def test_rejects_unsupported_type(self):
        from app.core.exceptions import AudioValidationError
        with pytest.raises(AudioValidationError) as exc:
            self.processor.validate_request("video/mp4", "100")
        assert exc.value.error_code == "unsupported_audio_type"

    def test_rejects_oversized_via_header(self):
        from app.core.exceptions import AudioValidationError
        with pytest.raises(AudioValidationError) as exc:
            self.processor.validate_request("audio/wav", str(10_000_000))
        assert exc.value.error_code == "upload_too_large"

    def test_byte_backstop_rejects_oversized(self):
        from app.core.exceptions import AudioValidationError
        with pytest.raises(AudioValidationError) as exc:
            self.processor.validate_bytes(b"\x00" * 10_000_000)
        assert exc.value.error_code == "upload_too_large"

    def test_byte_backstop_accepts_valid(self):
        # Should not raise
        self.processor.validate_bytes(b"\x00" * 1000)

    def test_normalize_content_type_strips_params(self):
        normalized = self.processor._normalize_content_type("audio/webm; codecs=opus")
        assert normalized == "audio/webm"

    def test_normalize_content_type_handles_aliases(self):
        normalized = self.processor._normalize_content_type("audio/x-wav")
        assert normalized == "audio/wav"

    def test_empty_content_type_fails(self):
        from app.core.exceptions import AudioValidationError
        with pytest.raises(AudioValidationError) as exc:
            self.processor.validate_request("", "100")
        assert exc.value.error_code == "unsupported_audio_type"

    def test_none_content_type_fails(self):
        from app.core.exceptions import AudioValidationError
        with pytest.raises(AudioValidationError):
            self.processor.validate_request(None, "100")

    def test_missing_content_length_returns_zero(self):
        size = self.processor.validate_request("audio/wav", "")
        assert size == 0

    def test_decode_normalizes_stereo_audio_to_mono_16khz_wav(self):
        source_rate = 48000
        seconds = 1
        timeline = np.linspace(0, seconds, source_rate * seconds, endpoint=False)
        left = (np.sin(2 * np.pi * 440 * timeline) * 12000).astype(np.int16)
        right = (np.sin(2 * np.pi * 660 * timeline) * 8000).astype(np.int16)
        stereo = np.column_stack((left, right)).reshape(-1)
        source = io.BytesIO()
        with wave.open(source, "wb") as wav:
            wav.setnchannels(2)
            wav.setsampwidth(2)
            wav.setframerate(source_rate)
            wav.writeframes(stereo.tobytes())

        normalized = self.processor.decode_and_normalize(source.getvalue())
        with wave.open(io.BytesIO(normalized), "rb") as wav:
            assert wav.getnchannels() == 1
            assert wav.getsampwidth() == 2
            assert wav.getframerate() == 16000
            assert abs(wav.getnframes() - 16000) <= 1
        assert self.processor.detect_silence(normalized) is False


# ═══════════════════════════════════════════════════════════════
# AudioProcessor — silence detection (numpy-only, no PyAV)
# ═══════════════════════════════════════════════════════════════

class TestAudioProcessorSilence:
    def setup_method(self):
        from app.services.audio_processor import AudioProcessor
        self.processor = AudioProcessor()
        self.sample_rate = 16000

    def _build_wav_bytes(self, samples_int16):
        """Build a valid WAV file from int16 samples using struct."""
        num_samples = len(samples_int16)
        data_size = num_samples * 2
        header = bytearray()
        header.extend(b"RIFF")
        header.extend(struct.pack("<I", 36 + data_size))
        header.extend(b"WAVEfmt ")
        header.extend(struct.pack("<IHHIIHH", 16, 1, 1, self.sample_rate,
                                  self.sample_rate * 2, 2, 16))
        header.extend(b"data")
        header.extend(struct.pack("<I", data_size))
        return bytes(header) + samples_int16.tobytes()

    def test_silent_audio_detected(self):
        """All-zero samples should be detected as silence."""
        samples = np.zeros(self.sample_rate, dtype=np.int16)  # 1 second of silence
        wav = self._build_wav_bytes(samples)
        assert self.processor.detect_silence(wav) is True

    def test_loud_audio_not_silent(self):
        """Consistent high-amplitude samples should NOT be silence."""
        samples = np.ones(self.sample_rate, dtype=np.int16) * 8000
        wav = self._build_wav_bytes(samples)
        assert self.processor.detect_silence(wav) is False

    def test_partial_silence_borderline(self):
        """Very quiet audio just below threshold should be silence."""
        samples = (np.ones(self.sample_rate, dtype=np.float32) * 100).astype(np.int16)
        wav = self._build_wav_bytes(samples)
        is_silent = self.processor.detect_silence(wav)
        # RMS of 100 in int16 range is very quiet (0.003 range)
        assert is_silent is True

    def test_empty_wav_header_returns_silent(self):
        """Audio shorter than 44 bytes (min WAV header) should be treated as silent."""
        assert self.processor.detect_silence(b"too short") is True

    def test_sine_wave_not_silent(self):
        """A 440Hz sine wave should not be detected as silence."""
        t = np.linspace(0, 1, self.sample_rate, endpoint=False)
        samples = (np.sin(2 * np.pi * 440 * t) * 16000).astype(np.int16)
        wav = self._build_wav_bytes(samples)
        assert self.processor.detect_silence(wav) is False


# ═══════════════════════════════════════════════════════════════
# AudioProcessor — WAV building
# ═══════════════════════════════════════════════════════════════

class TestAudioProcessorBuildWav:
    def setup_method(self):
        from app.services.audio_processor import AudioProcessor
        self.processor = AudioProcessor()

    def test_build_wav_has_valid_header(self):
        samples = np.array([100, 200, -100, -200], dtype=np.int16)
        wav = self.processor._build_wav(samples)
        # Check RIFF header
        assert wav[:4] == b"RIFF"
        assert wav[8:12] == b"WAVE"
        assert wav[12:16] == b"fmt "
        # Check PCM data
        data_offset = 44  # WAV header is 44 bytes for PCM
        assert len(wav) == 44 + len(samples) * 2
        # Verify first sample
        first_sample = struct.unpack("<h", wav[data_offset:data_offset + 2])[0]
        assert first_sample == 100


# ═══════════════════════════════════════════════════════════════
# AudioChunker
# ═══════════════════════════════════════════════════════════════

class TestAudioChunker:
    def _build_wav_seconds(self, seconds: int):
        from app.services.audio_processor import AudioProcessor

        sample_rate = 16000
        samples = np.ones(sample_rate * seconds, dtype=np.int16) * 1000
        return AudioProcessor()._build_wav(samples)

    def test_short_wav_returns_single_original_chunk(self):
        from app.services.audio_chunker import AudioChunker

        wav = self._build_wav_seconds(5)
        chunks = AudioChunker(chunk_seconds=10, overlap_seconds=2).split_wav(wav)
        assert len(chunks) == 1
        assert chunks[0].index == 0
        assert chunks[0].start_seconds == 0.0
        assert chunks[0].wav_bytes == wav

    def test_long_wav_splits_with_overlap(self):
        from app.services.audio_chunker import AudioChunker

        wav = self._build_wav_seconds(25)
        chunks = AudioChunker(chunk_seconds=10, overlap_seconds=2).split_wav(wav)
        assert len(chunks) == 3
        assert [round(chunk.start_seconds) for chunk in chunks] == [0, 8, 16]
        assert [round(chunk.end_seconds) for chunk in chunks] == [10, 18, 25]

    def test_overlap_must_be_smaller_than_chunk(self):
        from app.services.audio_chunker import AudioChunker

        with pytest.raises(ValueError):
            AudioChunker(chunk_seconds=10, overlap_seconds=10)


class TestFasterWhisperChunkMerging:
    def test_overlap_words_are_not_duplicated(self):
        from app.clients.voice.stt_engine.faster_whisper import FasterWhisperEngine

        parts = ["I built the backend with"]
        merged = FasterWhisperEngine._append_with_overlap_dedup(
            parts, "backend with React and Docker"
        )
        assert merged == ["I built the backend with", "React and Docker"]

    def test_non_overlapping_text_is_appended(self):
        from app.clients.voice.stt_engine.faster_whisper import FasterWhisperEngine

        merged = FasterWhisperEngine._append_with_overlap_dedup(
            ["I built the API"], "Then I deployed Docker"
        )
        assert merged == ["I built the API", "Then I deployed Docker"]


# ═══════════════════════════════════════════════════════════════
# Session — draft serialization (without Redis)
# ═══════════════════════════════════════════════════════════════

class TestSessionDraftSerialization:
    def test_draft_to_dict_roundtrip(self):
        from app.clients.voice.models import DraftData
        from app.clients.voice.session import VoiceSessionManager

        draft = DraftData(
            draft_id="draft_test",
            question_index=3,
            transcript="Test transcript",
            language="vi",
            stt_provider="google_stt",
            confidence=0.95,
            created_at="2026-06-18T12:00:00Z",
        )

        d = VoiceSessionManager._draft_to_dict(draft)
        assert d["draft_id"] == "draft_test"
        assert d["question_index"] == 3
        assert d["transcript"] == "Test transcript"

        # Roundtrip through JSON
        restored = json.loads(json.dumps(d))
        assert restored["draft_id"] == "draft_test"
        assert restored["confidence"] == 0.95


# ═══════════════════════════════════════════════════════════════
# Base engines — contract enforcement
# ═══════════════════════════════════════════════════════════════

class TestBaseEngines:
    def test_base_stt_engine_abstract(self):
        from app.clients.voice.stt_engine.base import BaseSTTEngine
        with pytest.raises(TypeError):
            BaseSTTEngine()  # abstract — can't instantiate

    def test_base_tts_engine_abstract(self):
        from app.clients.voice.tts_engine.base import BaseTTSEngine
        with pytest.raises(TypeError):
            BaseTTSEngine()  # abstract — can't instantiate

    def test_base_stt_has_transcribe(self):
        from app.clients.voice.stt_engine.base import BaseSTTEngine
        assert hasattr(BaseSTTEngine, "transcribe")
        assert callable(BaseSTTEngine.transcribe)

    def test_base_tts_has_synthesize(self):
        from app.clients.voice.tts_engine.base import BaseTTSEngine
        assert hasattr(BaseTTSEngine, "synthesize")
        assert callable(BaseTTSEngine.synthesize)


# ═══════════════════════════════════════════════════════════════
# Resample numpy utility
# ═══════════════════════════════════════════════════════════════

class TestResampleNumpy:
    def test_resample_same_rate_no_change(self):
        from app.services.audio_processor import AudioProcessor
        arr = np.array([[1.0, 2.0, 3.0, 4.0]], dtype=np.float32)
        result = AudioProcessor._resample_numpy(arr, 16000, 16000)
        assert result.shape == arr.shape
        np.testing.assert_array_almost_equal(result, arr)

    def test_resample_downsample(self):
        from app.services.audio_processor import AudioProcessor
        arr = np.array([[1.0, 2.0, 3.0, 4.0]], dtype=np.float32)
        result = AudioProcessor._resample_numpy(arr, 16000, 8000)
        assert result.shape[1] == 2  # half the length

    def test_resample_upsample(self):
        from app.services.audio_processor import AudioProcessor
        arr = np.array([[1.0, 2.0]], dtype=np.float32)
        result = AudioProcessor._resample_numpy(arr, 8000, 16000)
        assert result.shape[1] == 4  # double the length

    def test_resample_raises_on_stereo(self):
        from app.services.audio_processor import AudioProcessor
        arr = np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float32)  # stereo
        with pytest.raises(ValueError, match="mono"):
            AudioProcessor._resample_numpy(arr, 16000, 8000)
