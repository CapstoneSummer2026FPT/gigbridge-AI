from fastapi import (
    APIRouter,
    Depends,
    Form,
    File,
    Request,
    UploadFile,
    HTTPException,
    status,
)
from typing import Optional

from app.api.schemas.base import StandardResponse
from app.api.schemas.interviews import (
    StartInterviewRequest,
    SubmitAnswerRequest,
    ConfirmAnswerRequest,
    InterviewQuestionResponse,
    DraftDataResponse,
)
from app.core.exceptions import (
    VoiceProviderException,
    AudioValidationError,
    SessionExpiredError,
    DraftExpiredError,
    ConfirmConflictError,
)
from app.services.audio_processor import AudioProcessor
from app.services.interviews import InterviewService, get_interview_service

router = APIRouter(prefix="/interviews")

# ── Audio processor dependency ─────────────────────────────────

_audio_processor: Optional[AudioProcessor] = None


def get_audio_processor() -> AudioProcessor:
    global _audio_processor
    if _audio_processor is None:
        _audio_processor = AudioProcessor()
    return _audio_processor


# ── Error handler helper ────────────────────────────────────────

def _as_http(exc: Exception, default_status: int = 500) -> HTTPException:
    """Convert a known exception to an HTTPException with the right status."""
    if isinstance(exc, SessionExpiredError):
        return HTTPException(
            status_code=401,
            detail={"code": "session_not_found", "message": str(exc)},
        )
    if isinstance(exc, DraftExpiredError):
        return HTTPException(
            status_code=410,
            detail={"code": "draft_expired", "message": str(exc)},
        )
    if isinstance(exc, ConfirmConflictError):
        return HTTPException(
            status_code=409,
            detail={"code": "confirm_conflict", "message": str(exc)},
        )
    if isinstance(exc, AudioValidationError):
        return HTTPException(
            status_code=exc.status_code,
            detail={
                "code": exc.error_code,
                "message": exc.message,
                "errors": exc.errors,
            },
        )
    if isinstance(exc, VoiceProviderException):
        return HTTPException(
            status_code=503,
            detail={
                "code": "provider_unavailable",
                "message": str(exc),
                "errors": exc.errors,
            },
        )
    return HTTPException(status_code=default_status, detail=str(exc))


# ── Endpoints ───────────────────────────────────────────────────

@router.post(
    "/start",
    response_model=StandardResponse[InterviewQuestionResponse],
    status_code=status.HTTP_201_CREATED,
)
async def start_interview(
    request: StartInterviewRequest,
    service: InterviewService = Depends(get_interview_service),
):
    """Initialize an AI interview session.

    Generates the first question and TTS audio if voice mode is selected.
    Language defaults to Vietnamese (vi).
    """
    try:
        data = await service.initialize_interview(request)
        return StandardResponse(
            success=True,
            message="Interview session successfully initialized.",
            data=data,
            errors=[],
        )
    except Exception as exc:
        raise _as_http(exc)


@router.post(
    "/submit",
    response_model=StandardResponse[InterviewQuestionResponse],
    status_code=status.HTTP_200_OK,
)
async def submit_answer(
    request: SubmitAnswerRequest,
    service: InterviewService = Depends(get_interview_service),
):
    """Submit a written text response to the current question.

    Returns the next question or final evaluation.
    For voice interviews, use /transcribe-audio + /confirm-answer instead.
    """
    try:
        data = await service.process_answer(request.session_id, request.answer_text)
        return StandardResponse(
            success=True,
            message="Answer successfully processed.",
            data=data,
            errors=[],
        )
    except Exception as exc:
        raise _as_http(exc)


@router.post(
    "/transcribe-audio",
    response_model=StandardResponse[DraftDataResponse],
    status_code=status.HTTP_200_OK,
)
async def transcribe_audio(
    request: Request,
    session_id: str = Form(..., description="Active interview session ID"),
    audio_file: UploadFile = File(..., description="Recorded voice audio (webm, wav, mp3, mp4)"),
    language: Optional[str] = Form(None, description="BCP-47 language override"),
    service: InterviewService = Depends(get_interview_service),
    audio_proc: AudioProcessor = Depends(get_audio_processor),
):
    """Transcribe a voice recording and save a draft.

    Upload guard chain:
      1. Content-Type validated from headers (before reading body)
      2. Content-Length checked from headers (before reading body)
      3. Byte-length backstop after reading
      4. Universal decode via PyAV → WAV 16kHz mono PCM
      5. Silence detection on decoded PCM (meaningful RMS)
      6. STT transcription with auto-fallback on failure

    Returns a draft that must be confirmed via /confirm-answer.
    The draft expires after 10 minutes or after confirmation.
    """
    try:
        # 1. Validate Content-Type + Content-Length (before reading body)
        audio_proc.validate_request(
            audio_file.content_type,
            request.headers.get("content-length", "0"),
        )

        # 2. Read body
        audio_bytes = await audio_file.read()

        # 3. Hard byte backstop
        audio_proc.validate_bytes(audio_bytes)

        # 4. Universal decode → WAV 16kHz mono PCM (PyAV)
        pcm_wav_bytes = audio_proc.decode_and_normalize(audio_bytes)

        # 5. Silence detection on decoded PCM
        if audio_proc.detect_silence(pcm_wav_bytes):
            raise AudioValidationError("no_speech_detected", 400)

        # 6. Transcribe via service
        result = await service.transcribe_audio(session_id, pcm_wav_bytes, language)

        return StandardResponse(
            success=True,
            message="Audio transcribed successfully.",
            data=result,
            errors=[],
        )
    except Exception as exc:
        raise _as_http(exc)


@router.post(
    "/confirm-answer",
    response_model=StandardResponse[InterviewQuestionResponse],
    status_code=status.HTTP_200_OK,
)
async def confirm_answer(
    request: ConfirmAnswerRequest,
    service: InterviewService = Depends(get_interview_service),
):
    """Confirm a previously transcribed answer and advance the interview.

    Atomic flow:
      1. Consumes the draft via GETDEL (prevents double-confirm)
      2. Saves answer to Redis conversation history
      3. Generates next question via LLM
      4. Synthesizes TTS (cached per question)
      5. Advances the question pointer (ONLY after TTS confirmed)

    Error codes:
      - 401 session_not_found: Session expired or invalid
      - 410 draft_expired: Draft was already consumed or TTL expired
      - 409 confirm_conflict: Draft was already confirmed for this session
    """
    try:
        result = await service.confirm_answer(
            request.session_id, request.corrected_text
        )
        return StandardResponse(
            success=True,
            message="Answer confirmed. Next question ready.",
            data=result,
            errors=[],
        )
    except Exception as exc:
        raise _as_http(exc)


@router.post("/submit-audio", status_code=status.HTTP_410_GONE)
async def submit_audio_deprecated():
    """This endpoint has been replaced by /transcribe-audio + /confirm-answer.

    Returns 410 Gone with a message pointing to the new flow.
    """
    raise HTTPException(
        status_code=410,
        detail={
            "code": "endpoint_deprecated",
            "message": "Use /transcribe-audio + /confirm-answer instead.",
            "errors": ["endpoint_deprecated"],
        },
    )
