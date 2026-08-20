"""
PURPOSE: AI-assisted job description, title, and taxonomy field generation using RAG precision retrieval.
IMPORTANCE: Critical — Core feature enabling clients to write high-quality, structured job requirement posts.
READING FLOW: app/schemas/job_posts.py -> app/services/job_posts/job_post_base.py -> app/services/job_posts/job_details_generator.py -> app/api/routes/job_posts.py
"""

import logging
from app.schemas.job_posts import (
    JobPostDetailsGenerationResponse,
    JobPostGenerationRequest,
)
from app.schemas.rag import AnswerConfig, RetrievalGroup
from app.core.exceptions import AIServerException
from app.services.job_posts.job_post_base import JobPostBaseService

logger = logging.getLogger("ai_server.job_details_generator")


class JobDetailsGeneratorService(JobPostBaseService):
    """Generates structured job details, taxonomy IDs, and sanitized job description using RAG pipeline."""

    async def generate_job_details(
        self, request: JobPostGenerationRequest
    ) -> JobPostDetailsGenerationResponse:
        """Generate structured job details and description from client prompt.
        
        Flow:
        1. Detect target language (Vietnamese vs English).
        2. Format RAG precision config targeting taxonomy retrieval groups (majors, categories, skills).
        3. Invoke RAG query engine to answer question with structured response format.
        4. Validate safety policy violations (POLICY_VIOLATION).
        5. Clamp system and custom skill lists to a maximum of 10 skills.
        6. Sanitize description text by stripping redundant budget/timeline sections.
        7. Return JobPostDetailsGenerationResponse.
        """
        logger.info("Generating job details using RAG pipeline")
        target_lang = "Vietnamese" if self.is_vietnamese(request.client_prompt) else "English"

        system_prompt = (
            "You represent GigBridge, a professional freelance gig marketplace for IT and creative talent.\n"
            "You help clients write professional, detailed, and clear job descriptions.\n"
            "Review the client's questions and the lists of allowed database fields. "
            "Select the single best matching Major ID and Category ID. "
            "Identify matching System Skill IDs and supply relevant custom skills if needed.\n"
            "BUDGET AND TIMELINE ESTIMATION:\n"
            "- Honor any explicit budget/timeline stated by the user (1 GC = 1,000 VND).\n"
            "- When auto-estimating budget, estimate AS CHEAP AS POSSIBLE based on complexity (Small: 100-300 GC, Medium: 300-1000 GC, Complex/MVP: 1000-3000 GC).\n"
            "- When auto-estimating timeline, estimate AS FAST AS POSSIBLE (Small/Medium: 1 week, Complex: 2-3 weeks, max 1 month).\n"
            "SAFETY POLICY:\n"
            "- You MUST NOT generate job posts for illegal, harmful, or dangerous jobs.\n"
            "- If the client's prompt requests any such illegal activity, you MUST return title='POLICY_VIOLATION'.\n"
            "LANGUAGE CONSTRAINTS:\n"
            f"- You MUST generate both the 'title' and 'description' fields strictly in {target_lang}.\n"
            "- Custom skills can be in English or Vietnamese matching the prompt context."
        )

        config = AnswerConfig(
            style="precision",
            collection_name="ai-create-job-post",
            response_format=JobPostDetailsGenerationResponse,
            retrieval_groups=[
                RetrievalGroup(name="majors", n_results=10, where={"type": "major"}),
                RetrievalGroup(name="categories", n_results=15, where={"type": "category"}),
                RetrievalGroup(name="skills", n_results=15, where={"type": "skill"}),
            ],
            system_prompt=system_prompt,
            user_template="job_posts_details.txt"
        )

        result = await self.rag.answer_question(request.client_prompt, config)
        response_data = result.answer

        if isinstance(response_data, str):
            logger.error(f"Failed to parse job details structured output: {response_data}")
            raise AIServerException(
                message="The model generated an invalid job description response structure.",
                status_code=500,
                errors=["invalid_response_structure"]
            )

        if response_data.title == "POLICY_VIOLATION":
            logger.warning(f"Safety policy violation detected in prompt: {request.client_prompt}")
            raise AIServerException(
                message="The request violates platform safety guidelines against illegal or harmful activities.",
                status_code=400,
                errors=["policy_violation"]
            )

        total_system = len(response_data.system_skill_ids)
        if total_system > 10:
            response_data.system_skill_ids = response_data.system_skill_ids[:10]
            response_data.custom_skills = []
        elif total_system + len(response_data.custom_skills) > 10:
            response_data.custom_skills = response_data.custom_skills[:(10 - total_system)]

        if response_data.description:
            response_data.description = self.strip_budget_and_timeline_sections(response_data.description)

        # Post-validation: Ensure category_id is valid and belongs to major_id
        from app.services.job_posts.job_post_base import get_full_taxonomy
        taxonomy = get_full_taxonomy()
        valid_cats = taxonomy["categories_by_major"].get(response_data.major_id, [])
        valid_cat_ids = {c["category_id"] for c in valid_cats}

        if valid_cats and response_data.category_id not in valid_cat_ids:
            logger.warning(
                f"Model returned category_id {response_data.category_id} not belonging to major_id {response_data.major_id}. "
                f"Autocorrecting category_id to {valid_cats[0]['category_id']} ({valid_cats[0]['name']})."
            )
            response_data.category_id = valid_cats[0]["category_id"]

        return response_data
