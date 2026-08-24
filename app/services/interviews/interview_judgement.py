"""
PURPOSE: Candidate evaluation, technical answer scoring, AI detection verification, and interview feedback generation.
IMPORTANCE: Critical — Primary AI assessment module producing hiring recommendations and weighted vetting scores.
READING FLOW: app/schemas/interviews.py -> app/services/interviews/interview_base.py -> app/services/interviews/interview_judgement.py -> app/api/routes/interviews.py
"""

import logging
from pydantic import ValidationError

from app.schemas.interviews import (
    AnalyzeVettingRequest,
    InterviewFeedback,
)
from app.services.interviews.interview_base import InterviewBaseService

logger = logging.getLogger("ai_server.interview_judgement")


class InterviewJudgementService(InterviewBaseService):
    """Evaluates candidate performance, detects AI-generated content, and calculates weighted vetting scores."""

    async def generate_feedback(self, session_id: str) -> InterviewFeedback:
        """Generate evaluation feedback and overall hiring decision from full interview conversation history.
        
        Flow:
        1. Retrieve conversation history from Redis via VoiceService.
        2. Prompt LLM to evaluate technical accuracy, communication, and candidate suitability.
        3. Parse JSON response into structured InterviewFeedback object (with fallback JSON extraction).
        """
        history = await self.voice.get_history(session_id)

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
            response_format=InterviewFeedback,
        )

        raw_evaluation = evaluation_json if isinstance(evaluation_json, str) else ""
        try:
            return InterviewFeedback.model_validate_json(raw_evaluation)
        except (ValidationError, ValueError, TypeError):
            start = raw_evaluation.find("{")
            end = raw_evaluation.rfind("}")
            if start >= 0 and end > start:
                try:
                    return InterviewFeedback.model_validate_json(
                        raw_evaluation[start : end + 1]
                    )
                except (ValidationError, ValueError, TypeError):
                    pass
            logger.exception("LLM returned invalid interview feedback JSON")
            return InterviewFeedback(
                score=0,
                summary="Automated feedback is temporarily unavailable.",
                technical_skills=[],
                soft_skills=[],
                recommended_hire=False,
            )

    async def analyze_vetting(self, request: AnalyzeVettingRequest) -> InterviewFeedback:
        """Analyze candidate vetting Q&A pairs and calculate difficulty-weighted score.
        
        Flow:
        1. Format Q&A pairs into prompt text block.
        2. Prompt LLM to grade individual questions, check AI generation traits, and produce feedback.
        3. Parse structured InterviewFeedback object.
        4. Compute programmatic difficulty-weighted score across questions (easy: 1.0, medium: 1.5, hard: 2.0).
        5. Apply holistic adjustment and clamp final score between 0 and 100.
        """
        qa_lines = []
        for pair in request.qa_pairs:
            qa_lines.append(
                f"[Question {pair.question_index}] ({pair.question_text})\n"
                f"Candidate Answer: {pair.candidate_answer}\n"
                "---------------------"
            )
        qa_block = "\n".join(qa_lines)

        job_title = request.job_title.strip()
        job_description = (request.job_description or "").strip()
        job_skills = ", ".join(request.job_skills) if request.job_skills else "Software Engineering"

        system_prompt = (
            "You are an expert technical recruiter and hiring manager evaluating a candidate's vetting questions and answers.\n"
            "Analyze the provided questions and candidate answers and produce a structured evaluation report.\n"
            "\n"
            "For each question-answer pair:\n"
            "1. Identify the Question Text.\n"
            "2. Classify the Question Type: 'theoretical', 'problem_solving', or 'experience'.\n"
            "3. Classify the Question Difficulty: 'easy', 'medium', or 'hard'.\n"
            "4. Extract the Candidate's Answer.\n"
            "5. Evaluate Candidate Answer Authenticity & AI Detection (is_ai_generated, ai_confidence_score, ai_detection_reason).\n"
            "6. Grade the Candidate's Answer (Score 0-100).\n"
            "7. Provide a concise, recruiter-focused justification Feedback.\n"
            "\n"
            "Also provide overall evaluation (Recommended Hire, Summary, Assessed Skills, Holistic Adjustment).\n"
            "Output strictly in JSON according to the schema requested."
        )

        user_prompt = (
            "Evaluate the following candidate vetting answers from the recruiter's perspective:\n\n"
            f"Job Title: {job_title}\n"
            f"Job Description: {job_description}\n"
            f"Expected Skills: {job_skills}\n\n"
            "Vetting Questions & Answers:\n"
            f"{qa_block}"
        )

        evaluation_json = await self.llm.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_format=InterviewFeedback,
        )

        raw_evaluation = evaluation_json if isinstance(evaluation_json, str) else ""
        feedback = None
        try:
            feedback = InterviewFeedback.model_validate_json(raw_evaluation)
        except (ValidationError, ValueError, TypeError):
            start = raw_evaluation.find("{")
            end = raw_evaluation.rfind("}")
            if start >= 0 and end > start:
                try:
                    feedback = InterviewFeedback.model_validate_json(
                        raw_evaluation[start : end + 1]
                    )
                except (ValidationError, ValueError, TypeError):
                    pass

        if not feedback:
            logger.exception("LLM returned invalid vetting evaluation JSON")
            return InterviewFeedback(
                score=0,
                summary="Automated vetting feedback is temporarily unavailable.",
                technical_skills=[],
                soft_skills=[],
                recommended_hire=False,
                holistic_adjustment=0,
                holistic_adjustment_reason="Failed to parse AI response.",
                graded_questions=[],
            )

        feedback.score = self._calculate_weighted_score(
            feedback.graded_questions, feedback.holistic_adjustment
        )
        return feedback

    @staticmethod
    def _calculate_weighted_score(graded_questions: list, holistic_adjustment: int) -> int:
        """Calculate difficulty-weighted average score across graded question items."""
        difficulty_weights = {
            "easy": 1.0,
            "medium": 1.5,
            "hard": 2.0,
        }

        total_weighted_score = 0.0
        total_weight = 0.0

        for gq in graded_questions:
            if getattr(gq, "question_type", "").lower() == "experience":
                continue
            weight = difficulty_weights.get(getattr(gq, "difficulty", "").lower(), 1.0)
            total_weighted_score += getattr(gq, "score", 0) * weight
            total_weight += weight

        if total_weight > 0:
            base_score = total_weighted_score / total_weight
        else:
            base_score = 0.0

        final_score = int(round(base_score + holistic_adjustment))
        return max(0, min(100, final_score))
