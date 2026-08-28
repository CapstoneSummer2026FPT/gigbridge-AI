"""
PURPOSE: AI-assisted job description, title, and taxonomy field generation using RAG precision retrieval.
IMPORTANCE: Critical — Core feature enabling clients to write high-quality, structured job requirement posts.
READING FLOW: app/schemas/job_posts.py -> app/services/job_posts/job_post_base.py -> app/services/job_posts/job_details_generator.py -> app/api/routes/job_posts.py
"""

import logging
from typing import Dict, List
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
        self.validate_client_prompt(request.client_prompt)
        target_lang = "Vietnamese" if self.is_vietnamese(request.client_prompt) else "English"

        system_prompt = (
            "You represent GigBridge, a professional freelance gig marketplace for IT and creative talent.\n"
            "You help clients write professional, detailed, and clear job descriptions.\n"
            "Review the client's questions and the lists of allowed database fields. "
            "Select the single best matching Major ID and Category ID. "
            "Identify matching System Skill IDs and supply relevant custom skills if needed.\n"
            "BUDGET AND TIMELINE ESTIMATION:\n"
            "- If explicit single cost is provided, set budget_min = budget_max = exact cost (1 GC = 1,000 VND).\n"
            "- If explicit budget range is provided, compute average (min + max) / 2 and set BOTH budget_min and budget_max equal to the average.\n"
            "- If explicit timeline is provided, use that exact user-specified duration.\n"
            "- When auto-estimating budget (no user budget given), estimate based on complexity (Small: 100-1000 GC, Medium: 300-5000 GC, Complex: 1000-20000 GC).\n"
            "- When auto-estimating timeline (no user timeline given), estimate based on complexity (Small/Medium: 1-2 weeks, Complex: 1-3 months).\n"
            "SAFETY POLICY:\n"
            "- You MUST NOT generate job posts for illegal, harmful, or dangerous jobs.\n"
            "- If the client's prompt requests any such illegal activity, you MUST return title='POLICY_VIOLATION'.\n"
            "- If the prompt is meaningless, off-topic, gibberish, or greetings-only (e.g. 'hihi', 'hello', 'asdf'), you MUST return title='INVALID_PROMPT'.\n"
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

        if response_data.title == "INVALID_PROMPT":
            logger.warning(f"Invalid or meaningless prompt detected by LLM: {request.client_prompt}")
            raise AIServerException(
                message="The prompt provided is invalid or meaningless. Please describe your project requirements in detail.",
                status_code=400,
                errors=["invalid_prompt"]
            )

        total_system = len(response_data.system_skill_ids)
        if total_system > 10:
            response_data.system_skill_ids = response_data.system_skill_ids[:10]
            response_data.custom_skills = []
        elif total_system + len(response_data.custom_skills) > 10:
            response_data.custom_skills = response_data.custom_skills[:(10 - total_system)]

        # Fallback safeguard: If both system_skill_ids and custom_skills are empty, auto-populate skills from taxonomy
        if not response_data.system_skill_ids and not response_data.custom_skills:
            from app.services.job_posts.job_post_base import get_full_taxonomy
            taxonomy = get_full_taxonomy()
            all_taxonomy_skills = taxonomy.get("skills", [])
            if all_taxonomy_skills:
                # Take top 5 skills as fallback
                response_data.system_skill_ids = [s["skill_id"] for s in all_taxonomy_skills[:5]]
                logger.info(f"Auto-populated {len(response_data.system_skill_ids)} fallback skill IDs for prompt: {request.client_prompt}")

        if response_data.description:
            response_data.description = self.strip_budget_and_timeline_sections(response_data.description)

        # Post-validation: Ensure category_id is valid, belongs to major_id, and matches prompt intent
        from app.services.job_posts.job_post_base import get_full_taxonomy
        taxonomy = get_full_taxonomy()
        valid_cats = taxonomy["categories_by_major"].get(response_data.major_id, [])
        valid_cat_ids = {c["category_id"] for c in valid_cats}

        if valid_cats:
            best_cat_id = self.match_best_category(request.client_prompt, response_data.title, valid_cats)
            current_cat_name = next((c["name"] for c in valid_cats if c["category_id"] == response_data.category_id), "")

            # If category_id does not belong to major, or if there is an explicit role mismatch (e.g. prompt is Fullstack/Frontend/Backend but category was set to Cloud Engineer)
            is_mismatched = False
            combined = f"{response_data.title} {request.client_prompt}".lower()
            if any(kw in combined for kw in ["fullstack", "full-stack", "full stack"]) and current_cat_name != "Full-stack Developer":
                is_mismatched = True
            elif any(kw in combined for kw in ["frontend", "front-end", "front end"]) and current_cat_name not in ["Front-end Developer", "Full-stack Developer", "Web Designer"]:
                is_mismatched = True
            elif any(kw in combined for kw in ["backend", "back-end", "back end"]) and current_cat_name not in ["Back-end Developer", "Full-stack Developer"]:
                is_mismatched = True

            if response_data.category_id not in valid_cat_ids or is_mismatched:
                if best_cat_id:
                    target_name = next((c["name"] for c in valid_cats if c["category_id"] == best_cat_id), best_cat_id)
                    logger.warning(
                        f"Autocorrecting category_id from '{current_cat_name}' ({response_data.category_id}) "
                        f"to smart match '{target_name}' ({best_cat_id}) for title '{response_data.title}'."
                    )
                    response_data.category_id = best_cat_id

        return response_data

    @staticmethod
    def match_best_category(prompt_text: str, title: str, valid_cats: List[Dict[str, str]]) -> str:
        """Find the best matching category_id from valid_cats based on prompt and title keywords."""
        if not valid_cats:
            return ""

        import re
        combined_text = f"{title} {prompt_text}".lower()

        # Priority direct keyword mappings
        keyword_mappings = [
            (["fullstack", "full-stack", "full stack"], "Full-stack Developer"),
            (["frontend", "front-end", "front end", "react", "vue", "angular"], "Front-end Developer"),
            (["backend", "back-end", "back end", "node", "django", "laravel", "express", "spring"], "Back-end Developer"),
            (["mobile", "flutter", "react native", "android", "ios", "swift", "kotlin"], "Mobile App Developer"),
            (["ui/ux", "ui designer", "ux designer"], "UI/UX Designer"),
            (["data analyst", "analytics"], "Data Analyst"),
            (["data engineer"], "Data Engineer"),
            (["data scientist"], "Data Scientist"),
            (["ai", "machine learning", "llm", "prompt engineer"], "AI Automation Specialist"),
            (["devops", "ci/cd", "kubernetes", "docker"], "DevOps Engineer"),
            (["qa", "tester", "testing"], "QA Automation Engineer"),
            (["cloud", "aws", "azure", "gcp"], "Cloud Engineer"),
            (["wordpress"], "WordPress Developer"),
            (["shopify"], "Shopify Developer"),
        ]

        for keywords, target_name in keyword_mappings:
            if any(kw in combined_text for kw in keywords):
                for cat in valid_cats:
                    if cat["name"].lower() == target_name.lower():
                        return cat["category_id"]

        # Word overlap scoring fallback
        best_cat_id = valid_cats[0]["category_id"]
        max_score = -1
        words = set(re.findall(r"\b\w+\b", combined_text))

        for cat in valid_cats:
            cat_words = set(re.findall(r"\b\w+\b", cat["name"].lower()))
            overlap = len(words & cat_words)
            if overlap > max_score:
                max_score = overlap
                best_cat_id = cat["category_id"]

        return best_cat_id


