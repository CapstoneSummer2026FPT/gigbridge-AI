"""
PURPOSE: AI milestone hiring plan and recruitment vetting questions generator with mathematical budget/duration clamping.
IMPORTANCE: Critical — Generates milestone budget breakdowns and vetting questions for client job posts.
READING FLOW: app/schemas/job_posts.py -> app/services/job_posts/job_post_base.py -> app/services/job_posts/hiring_plan_generator.py -> app/api/routes/job_posts.py
"""

from datetime import date, timedelta
import logging
from app.schemas.job_posts import (
    JobPostHiringPlanGenerationRequest,
    JobPostHiringPlanGenerationResponse,
)
from app.schemas.rag import AnswerConfig
from app.core.exceptions import AIServerException
from app.services.job_posts.job_post_base import JobPostBaseService

logger = logging.getLogger("ai_server.hiring_plan_generator")


class HiringPlanGeneratorService(JobPostBaseService):
    """Generates vetting questions and mathematically clamped project milestones."""

    async def generate_job_hiring_plan(
        self, request: JobPostHiringPlanGenerationRequest
    ) -> JobPostHiringPlanGenerationResponse:
        """Generate recruitment vetting questions and milestone breakdown from approved job post details.
        
        Flow:
        1. Detect prompt language (Vietnamese vs English).
        2. Compute canonical approved budget and timeline weeks.
        3. Clamp proposal closing date to a maximum of 21 days from today.
        4. Format LLM prompt with explicit numeric budget/timeline constraint blocks.
        5. Invoke RAG query engine with JobPostHiringPlanGenerationResponse format.
        6. Apply post-generation deterministic mathematical clamping:
           - Scale milestone amounts to sum EXACTLY to approved_budget.
           - Scale milestone durations so total weeks equal approved_weeks.
           - Recalculate milestone due dates sequentially starting strictly from current day.
        7. Append mandatory compulsory experience question and return.
        """
        logger.info("Generating job hiring plan using RAG pipeline")
        target_lang = "Vietnamese" if self.is_vietnamese(request.client_prompt) else "English"

        system_prompt = (
            "You represent GigBridge, a professional freelance gig marketplace for IT and creative talent.\n"
            "You help clients write professional milestone plans and vetting questions for their projects.\n"
            "SAFETY POLICY:\n"
            "- You MUST NOT generate hiring plans for illegal, harmful, or dangerous jobs.\n"
            "- If the provided context indicates illegal activity, you MUST return empty lists.\n"
            "LANGUAGE CONSTRAINTS:\n"
            f"- You MUST generate all text fields strictly in {target_lang}."
        )

        approved_budget = self.resolve_canonical_budget(request.budget_min, request.budget_max)
        approved_weeks = self.parse_duration_to_weeks(request.estimated_duration or "")

        max_proposal_date = date.today() + timedelta(days=21)
        raw_closing = self.convert_date_to_iso(request.proposal_closing_date)
        try:
            parsed_closing = date.fromisoformat(raw_closing)
            clamped_closing = min(parsed_closing, max_proposal_date).isoformat()
        except Exception:
            clamped_closing = max_proposal_date.isoformat()

        constraint_block = (
            f"\n\nHARD CONSTRAINTS — these are code-enforced and must not be violated:\n"
            f"- Total milestone budget MUST sum to EXACTLY {approved_budget:.2f} GC\n"
            f"- Total milestone duration MUST NOT exceed {approved_weeks:.1f} weeks\n"
            f"- Each individual milestone duration must be expressed as 'N weeks' (integer only).\n"
            f"- Proposal closing date MUST NOT exceed 3 weeks (21 days) from today (max: {clamped_closing})."
        )

        combined_prompt = (
            f"Original user requirement:\n{request.client_prompt}\n\n"
            f"Generated/Approved Job Details:\n"
            f"Title: {request.title}\n"
            f"Description: {request.description}\n"
            f"Approved Budget: {approved_budget:.2f} GC\n"
            f"Approved Duration: {request.estimated_duration}"
            f"{constraint_block}"
        )

        config = AnswerConfig(
            style="precision",
            collection_name="ai-create-job-post",
            response_format=JobPostHiringPlanGenerationResponse,
            retrieval_groups=[],
            system_prompt=system_prompt,
            user_template="job_posts_hiring_plan.txt"
        )

        result = await self.rag.answer_question(combined_prompt, config)
        response_data = result.answer

        if isinstance(response_data, str):
            logger.error(f"Failed to parse hiring plan structured output: {response_data}")
            raise AIServerException(
                message="The model generated an invalid hiring plan response structure.",
                status_code=500,
                errors=["invalid_response_structure"]
            )

        if response_data.milestones:
            for milestone in response_data.milestones:
                milestone.due_date = self.convert_date_to_iso(milestone.due_date)

            self.clamp_milestone_budgets(response_data.milestones, approved_budget)
            self.clamp_milestone_durations(response_data.milestones, approved_weeks)
            self.recalculate_due_dates(response_data.milestones, date.today())

        compulsory_question = "Bạn có bao nhiêu kinh nghiệm cho vai trò này?" if target_lang == "Vietnamese" else "How many experiences do you have for this role?"
        raw_questions = response_data.question_recruitment or []
        filtered_questions = [
            q for q in raw_questions
            if "how many experiences" not in q.lower() and "bao nhiêu kinh nghiệm" not in q.lower()
        ]
        response_data.question_recruitment = filtered_questions[:3] + [compulsory_question]

        return response_data
