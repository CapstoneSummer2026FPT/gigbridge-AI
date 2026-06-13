import uuid
import json
import logging
from typing import List, Dict, Any, Optional
from app.api.schemas.interviews import StartInterviewRequest, InterviewQuestionResponse, InterviewFeedback
from app.clients.llm.gateway import LLMGateway, get_llm_gateway
from app.services.memory import MemoryManager, get_memory_manager
from app.services.voice import VoiceService, get_voice_service

logger = logging.getLogger("ai_server.interviews_service")

class InterviewService:
    """Service handling stateful, voice-enabled AI candidate screening interviews"""
    
    def __init__(
        self,
        llm_gateway: LLMGateway = get_llm_gateway(),
        memory_manager: MemoryManager = get_memory_manager(),
        voice_service: VoiceService = get_voice_service()
    ):
        self.llm = llm_gateway
        self.memory = memory_manager
        self.voice = voice_service
        # Limit interview length to 3 rounds of questions for prototype
        self.max_questions = 3

    async def initialize_interview(self, request: StartInterviewRequest) -> InterviewQuestionResponse:
        session_id = f"int_{uuid.uuid4().hex[:12]}"
        logger.info(f"Initializing interview session: {session_id} for freelancer: {request.freelancer_id}")
        
        # Clear previous history if any
        await self.memory.clear_conversation_history(session_id)
        
        # Save session config to domain memories
        session_state = {
            "job_id": request.job_id,
            "freelancer_id": request.freelancer_id,
            "mode": request.mode,
            "question_index": 1,
            "questions_asked": []
        }
        await self.memory.save_domain_context("interviews", session_id, session_state)

        # Retrieve job details (simulate database fallback, check domain memory or default)
        job_details = await self.memory.get_domain_context("job_posts", request.job_id)
        job_title = job_details.get("title", "Software Developer") if job_details else "Software Developer"
        job_skills = job_details.get("skills", ["React", "API Integration"]) if job_details else ["Software Engineering"]

        system_prompt = (
            "You are an AI Technical Recruiter conducting an interview on behalf of GigBridge.\n"
            "Keep questions concise, professional, and targeted at assessing specific technical skills.\n"
            "Ask only one question at a time. Introduce yourself and ask the first question."
        )

        user_prompt = (
            f"Start the interview for a {job_title} position.\n"
            f"Key Skills to evaluate: {', '.join(job_skills)}.\n"
            "Generate the first ice-breaker technical question."
        )

        first_question = await self.llm.generate(system_prompt=system_prompt, user_prompt=user_prompt)
        
        # Save question to conversation history & state
        await self.memory.add_to_conversation_history(session_id, "assistant", first_question)
        session_state["questions_asked"].append(first_question)
        await self.memory.save_domain_context("interviews", session_id, session_state)

        # TTS Synthesis if voice mode chosen
        audio_base64 = None
        if request.mode == "voice":
            audio_base64 = await self.voice.text_to_speech(first_question)

        return InterviewQuestionResponse(
            session_id=session_id,
            question_index=1,
            question_text=first_question,
            audio_base64=audio_base64,
            is_completed=False
        )

    async def process_answer(self, session_id: str, answer_text: str) -> InterviewQuestionResponse:
        logger.info(f"Processing candidate answer for session: {session_id}")
        
        # Load state
        state = await self.memory.get_domain_context("interviews", session_id)
        if not state:
            raise ValueError("Interview session not found or has expired.")

        # Save user answer to history
        await self.memory.add_to_conversation_history(session_id, "user", answer_text)
        
        current_index = state["question_index"]
        
        if current_index >= self.max_questions:
            # Interview is complete! Let's generate evaluation feedback
            logger.info(f"Interview round limit reached. Grading candidate for session: {session_id}")
            
            history = await self.memory.get_conversation_history(session_id, limit=20)
            
            system_prompt = (
                "You are an expert technical interviewer evaluating a candidate's transcript.\n"
                "Evaluate the candidate transcript and return a final hiring decision.\n"
                "Output ONLY a JSON object matching this schema:\n"
                "{\n"
                '  "score": 85,\n'
                '  "summary": "Detailed summary...",\n'
                '  "technical_skills": ["React", "API Integration"],\n'
                '  "soft_skills": ["Communication"],\n'
                '  "recommended_hire": true\n'
                "}"
            )
            
            user_prompt = "Perform the evaluation on the conversation history provided."
            
            evaluation_json = await self.llm.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                history=history,
                response_format=InterviewFeedback
            )
            
            feedback_data = InterviewFeedback.model_validate_json(evaluation_json)
            
            # Update state
            state["is_completed"] = True
            await self.memory.save_domain_context("interviews", session_id, state)
            
            return InterviewQuestionResponse(
                session_id=session_id,
                question_index=current_index,
                is_completed=True,
                feedback=feedback_data
            )
        else:
            # Generate next question
            next_index = current_index + 1
            logger.info(f"Generating question {next_index} for session: {session_id}")
            
            history = await self.memory.get_conversation_history(session_id, limit=20)
            
            system_prompt = (
                "You are an AI Technical Recruiter conducting an interview on behalf of GigBridge.\n"
                "Analyze the transcript and user's answers. Ask the next follow-up question to probe deeper.\n"
                "Keep questions concise, professional, and ask only one question at a time."
            )
            
            user_prompt = "Generate the next question based on the candidate's last response."
            
            next_question = await self.llm.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                history=history
            )
            
            # Update state & history
            await self.memory.add_to_conversation_history(session_id, "assistant", next_question)
            state["question_index"] = next_index
            state["questions_asked"].append(next_question)
            await self.memory.save_domain_context("interviews", session_id, state)
            
            # TTS Synthesis if voice mode chosen
            audio_base64 = None
            if state["mode"] == "voice":
                audio_base64 = await self.voice.text_to_speech(next_question)

            return InterviewQuestionResponse(
                session_id=session_id,
                question_index=next_index,
                question_text=next_question,
                audio_base64=audio_base64,
                is_completed=False
            )

    async def process_audio_answer(self, session_id: str, audio_bytes: bytes, filename: str) -> InterviewQuestionResponse:
        """
        Transcribes audio bytes to text and processes it as an answer.
        """
        # Call STT
        transcription = await self.voice.speech_to_text(audio_bytes, filename)
        logger.info(f"Voice answer transcribed successfully: '{transcription}'")
        return await self.process_answer(session_id, transcription)

# Dependency helper
def get_interview_service() -> InterviewService:
    return InterviewService()
