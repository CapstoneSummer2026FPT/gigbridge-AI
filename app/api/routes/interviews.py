from fastapi import APIRouter, Depends, status, UploadFile, File, Form
from app.api.schemas.base import StandardResponse
from app.api.schemas.interviews import StartInterviewRequest, SubmitAnswerRequest, InterviewQuestionResponse
from app.services.interviews import InterviewService, get_interview_service

router = APIRouter(prefix="/interviews")

@router.post(
    "/start",
    response_model=StandardResponse[InterviewQuestionResponse],
    status_code=status.HTTP_201_CREATED
)
async def start_interview(
    request: StartInterviewRequest,
    service: InterviewService = Depends(get_interview_service)
):
    """
    Initialize an AI interview session. Generates the first question and TTS audio if voice mode is chosen.
    """
    data = await service.initialize_interview(request)
    return StandardResponse(
        success=True,
        message="Interview session successfully initialized.",
        data=data,
        errors=[]
    )

@router.post(
    "/submit",
    response_model=StandardResponse[InterviewQuestionResponse],
    status_code=status.HTTP_200_OK
)
async def submit_answer(
    request: SubmitAnswerRequest,
    service: InterviewService = Depends(get_interview_service)
):
    """
    Submit a written text response to the current question. Returns the next question or final evaluation.
    """
    data = await service.process_answer(request.session_id, request.answer_text)
    return StandardResponse(
        success=True,
        message="Answer successfully processed.",
        data=data,
        errors=[]
    )

@router.post(
    "/submit-audio",
    response_model=StandardResponse[InterviewQuestionResponse],
    status_code=status.HTTP_200_OK
)
async def submit_audio_answer(
    session_id: str = Form(..., description="Active interview session ID"),
    audio_file: UploadFile = File(..., description="Recorded candidate voice file (M4A/MP3/WAV)"),
    service: InterviewService = Depends(get_interview_service)
):
    """
    Submit a recorded voice response. Transcribes the audio, logs it, and returns the next question.
    """
    # Read the audio bytes
    audio_bytes = await audio_file.read()
    data = await service.process_audio_answer(session_id, audio_bytes, audio_file.filename)
    return StandardResponse(
        success=True,
        message="Voice answer transcribed and processed.",
        data=data,
        errors=[]
    )
