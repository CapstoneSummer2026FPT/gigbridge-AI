"""
PURPOSE: Stateful interview session initialization, text question generation, and session pointer orchestration.
IMPORTANCE: Critical — Primary session manager driving candidate screening sessions and LLM interview questions.
READING FLOW: app/schemas/interviews.py -> app/services/interviews/interview_base.py -> app/services/interviews/interview_session.py -> app/api/routes/interviews.py
"""

import hashlib
import logging
import secrets
import time
from typing import Optional

from app.schemas.interviews import (
    InterviewQuestionResponse,
    StartInterviewRequest,
)
from app.core.config import settings
from app.core.exceptions import SessionExpiredError
from app.services.interviews.interview_base import InterviewBaseService

logger = logging.getLogger("ai_server.interview_session")


class InterviewSessionService(InterviewBaseService):
    """Manages stateful candidate interview sessions and question generation."""

    async def initialize_interview(
        self, request: StartInterviewRequest
    ) -> InterviewQuestionResponse:
        """Initialize a new interview session in Redis and generate/retrieve the first question.
        
        Flow:
        1. Clean job title, description, skills, and phonetic aliases.
        2. Resolve language and resolve hotword vocabulary list.
        3. Create Redis-backed session data structure with access tokens.
        4. Generate first question via LLM (or pick first predefined question).
        5. Save assistant question to Redis history.
        6. Return InterviewQuestionResponse.
        """
        started_at = time.perf_counter()
        job_title = request.job_title.strip()
        job_description = (request.job_description or "").strip()
        job_skills = self.clean_terms(request.job_skills)
        job_phonetic_aliases = self.clean_aliases(request.job_phonetic_aliases)
        hotwords = self.hotword_resolver.resolve(
            job_title,
            job_skills,
            job_major=request.job_major,
            job_category=request.job_category,
            job_questions=request.job_questions,
            phonetic_aliases=job_phonetic_aliases,
        )
        interview_language = self.resolve_interview_language(
            request.language,
            job_title,
            job_description,
        )
        audio_access_token = secrets.token_urlsafe(32)

        session_data = {
            "job_id": request.job_id,
            "freelancer_id": request.freelancer_id,
            "mode": request.mode or "text",
            "language": interview_language,
            "stt_language": (request.language or "auto").strip().lower(),
            "audio_access_token_hash": hashlib.sha256(
                audio_access_token.encode("utf-8")
            ).hexdigest(),
            "question_index": 1,
            "question_count": (
                len(request.job_questions)
                if request.job_questions
                else request.question_count or self.max_questions
            ),
            "job_title": job_title,
            "job_description": job_description,
            "job_skills": job_skills,
            "hotwords": hotwords,
            "job_phonetic_aliases": job_phonetic_aliases,
            "job_questions": request.job_questions or [],
        }

        session_create_started = time.perf_counter()
        session = await self.voice.create_session(session_data)
        session_create_ms = (time.perf_counter() - session_create_started) * 1000
        logger.info(
            "Interview initialized: %s (lang=%s, mode=%s)",
            session.session_id, session.language, session.mode,
        )

        job_title = session.job_title
        job_description = session.job_description
        job_skills = session.job_skills or []
        skill_line = ", ".join(job_skills) if job_skills else "No structured skills were supplied; infer from the job description."
        language_name = self.language_name(session.language)

        system_prompt = (
            "You are an AI Technical Recruiter conducting an interview on behalf of GigBridge.\n"
            "Keep questions concise, professional, and targeted at assessing specific technical skills.\n"
            "Ask only one question at a time. Keep the response natural for a spoken interview.\n"
            f"Respond only in {language_name}. Keep programming languages, frameworks, tools, and product names unchanged."
        )
        user_prompt = (
            f"Start the interview for a {job_title} position.\n"
            f"Job requirements: {job_description or 'No job description was supplied.'}\n"
            f"Key skills to evaluate: {skill_line}.\n"
            "Generate the first ice-breaker technical question."
        )

        llm_started = time.perf_counter()
        if session.job_questions:
            first_question = session.job_questions[0]
            llm_ms = 0.0
        else:
            first_question = await self.llm.generate(
                system_prompt=system_prompt, user_prompt=user_prompt
            )
            llm_ms = (time.perf_counter() - llm_started) * 1000

        history_started = time.perf_counter()
        await self.voice.add_history(
            session.session_id, "assistant", first_question, session.language
        )
        history_ms = (time.perf_counter() - history_started) * 1000

        tts_provider = "streaming" if session.mode == "voice" else None
        total_ms = (time.perf_counter() - started_at) * 1000
        logger.info(
            "Interview initialize timing: session=%s total=%.0fms redis_create=%.0fms llm=%.0fms history=%.0fms mode=%s",
            session.session_id,
            total_ms,
            session_create_ms,
            llm_ms,
            history_ms,
            session.mode,
        )

        return InterviewQuestionResponse(
            session_id=session.session_id,
            audio_access_token=audio_access_token,
            question_index=1,
            question_count=len(session.job_questions) or session.question_count,
            question_text=first_question,
            language=session.language,
            audio_base64=None,
            audio_mime_type=None,
            tts_provider=tts_provider,
            fallback_used=False,
            is_completed=False,
            job_id=session.job_id,
            freelancer_id=session.freelancer_id,
        )

    async def process_answer(
        self, session_id: str, answer_text: str, feedback_generator=None
    ) -> InterviewQuestionResponse:
        """Process a text-mode answer, record to history, and generate the next question.
        
        Flow:
        1. Load session from Redis (fail fast if expired).
        2. Save candidate's text answer into Redis conversation history.
        3. If question limit reached, call feedback generator and return completed response.
        4. Otherwise, generate next question using LLM over conversation history.
        5. Advance question index pointer and save assistant question to history.
        6. Return InterviewQuestionResponse for the next question.
        """
        session = await self.voice.load_session(session_id)
        if not session:
            raise SessionExpiredError()

        await self.voice.add_history(
            session_id, "user", answer_text, session.language
        )

        question_count = len(session.job_questions) or session.question_count
        if session.question_index >= question_count:
            feedback = None
            if feedback_generator:
                feedback = await feedback_generator(session_id)
            return InterviewQuestionResponse(
                session_id=session_id,
                question_index=session.question_index,
                question_count=question_count,
                is_completed=True,
                feedback=feedback,
                job_id=session.job_id,
                freelancer_id=session.freelancer_id,
            )

        next_index = session.question_index + 1
        history = await self.voice.get_history(session_id)
        next_question = await self.generate_next_question(history, session.language)

        tts_provider = "streaming" if session.mode == "voice" else None
        await self.voice.advance_pointer(session_id)

        await self.voice.add_history(
            session_id, "assistant", next_question, session.language
        )
        return InterviewQuestionResponse(
            session_id=session_id,
            question_index=next_index,
            question_count=question_count,
            question_text=next_question,
            language=session.language,
            audio_base64=None,
            audio_mime_type=None,
            tts_provider=tts_provider,
            fallback_used=False,
            is_completed=False,
            job_id=session.job_id,
            freelancer_id=session.freelancer_id,
        )

    async def generate_next_question(self, history: list[dict], language: str) -> str:
        """Generate the next technical interview question using LLM over conversation history."""
        language_name = self.language_name(language)
        system_prompt = (
            "You are an AI Technical Recruiter conducting an interview on behalf of GigBridge.\n"
            "Analyze the transcript and user's answers. Ask the next follow-up question "
            "to probe deeper into their technical experience.\n"
            "Keep questions concise, professional, and ask only one question at a time.\n"
            f"Respond only in {language_name}. Keep programming languages, frameworks, tools, and product names unchanged."
        )
        user_prompt = "Generate the next question based on the candidate's last response."

        return await self.llm.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            history=history,
        )
