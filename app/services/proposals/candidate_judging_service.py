"""
PURPOSE: Candidate Evaluation Service combining LLM Qualitative Feature Extraction with Python Deterministic Mathematical Aggregation.
IMPORTANCE: Critical — Evaluates proposals and vetting Q&A screening answers, extracts verifiable evidence claims, and computes capped value scores.
"""

import asyncio
import json
import logging
from typing import List, Optional
from pydantic import ValidationError

from app.clients.llm.gateway import LLMGateway, get_llm_gateway
from app.schemas.candidate_judging_schemas import (
    CandidateJudgingRequest,
    CandidateJudgingResponse,
    BatchCandidateJudgingRequest,
    BatchCandidateJudgingResponse,
    LLMQualitativeEvaluation,
    JobPostBaselineDto,
    ProposalOfferDto,
)
from app.services.proposals.deterministic_calculator import DeterministicCalculator

logger = logging.getLogger("ai_server.candidate_judging_service")


class CandidateJudgingService:
    """Service performing evidence-backed LLM qualitative judging & deterministic score calculation."""

    def __init__(self, llm_gateway: Optional[LLMGateway] = None):
        self.llm = llm_gateway or get_llm_gateway()

    async def evaluate_candidate(
        self, request: CandidateJudgingRequest
    ) -> CandidateJudgingResponse:
        """Perform single-pass qualitative evaluation and deterministic calculation for one candidate."""
        baseline = request.job_post_baseline
        proposal = request.candidate_proposal

        system_prompt = (
            "You are an expert AI Technical Evaluator and Hiring Judge for GigBridge, a freelance IT marketplace.\n"
            "Evaluate the candidate's proposal and screening Q&A answers against the specific job post requirements.\n\n"
            "DYNAMIC FAIRNESS & CONSTRAINTS RULE:\n"
            "- DO NOT hardcode specific technologies as mandatory rules unless explicitly mentioned in this job description.\n"
            "- Dynamically extract technical requirements and constraints directly from the job title, description, and required skills.\n"
            "- Evaluate candidate responses strictly against the explicit constraints of THIS specific job post.\n\n"
            "ANTI-VERBOSITY & SUBSTANCE GUARDRAIL:\n"
            "- NEVER reward answer length or word count.\n"
            "- Evaluate technical substance, concise precision, and high information density.\n"
            "- Concise 1-3 sentence answers providing exact technical facts score HIGHER than wordy 500-word fluff essays.\n"
            "- Apply a verbosity penalty for padded fluff or generic filler phrases ('As a passionate developer...').\n\n"
            "EVIDENCE TRACE REQUIREMENT:\n"
            "- For EVERY subcriteria score (0-100), extract concrete evidence claims from the proposal/answers.\n"
            "- Include exact claim text, source field location (e.g. 'proposal.solutionApproach', 'answer_1'), and assessment ('Correct', 'Incorrect', 'Partial', 'Feasible', 'Unclear').\n\n"
            "REQUIREMENT FULFILLMENT MAPPING:\n"
            "- Map each explicit job post requirement/deliverable to candidate's edited milestones.\n"
            "- Mark is_fulfilled as true if covered in candidate milestones, else false.\n\n"
            "OUTPUT FORMAT:\n"
            "Output strictly valid JSON matching the LLMQualitativeEvaluation schema."
        )

        # Format original milestones
        orig_ms_block = "\n".join(
            f"- [{ms.order_index}] {ms.title} ({ms.amount} GC, {ms.estimated_duration or 'N/A'}): {ms.deliverables or 'N/A'}"
            for ms in baseline.original_milestones
        ) if baseline.original_milestones else "None specified"

        # Format edited milestones
        edited_ms_block = "\n".join(
            f"- [{ms.order_index}] {ms.title} ({ms.amount} GC, {ms.estimated_duration or 'N/A'}): {ms.deliverables or 'N/A'}"
            for ms in proposal.edited_milestones
        ) if proposal.edited_milestones else "None specified"

        # Format vetting Q&A answers
        qa_block = "\n".join(
            f"Question {qa.question_index}: {qa.question_text}\n"
            f"Candidate Answer: {qa.candidate_answer}\n"
            "-------------------"
            for qa in proposal.vetting_qa_answers
        ) if proposal.vetting_qa_answers else "No screening questions answered."

        user_prompt = (
            "CLIENT JOB POST BASELINE (Ground Truth):\n"
            f"Job Title: {baseline.job_title}\n"
            f"Description: {baseline.job_description}\n"
            f"Required Skills: {', '.join(baseline.required_skills) if baseline.required_skills else 'N/A'}\n"
            f"Target Budget Range: {baseline.budget_min or 0} - {baseline.budget_max or 0} GC\n"
            f"Target Duration: {baseline.estimated_duration or 'N/A'}\n"
            f"Original Client Milestones:\n{orig_ms_block}\n\n"
            "FREELANCER CANDIDATE PROPOSAL OFFER:\n"
            f"Proposal ID: {proposal.proposal_id}\n"
            f"Proposed Total Budget: {proposal.proposed_budget} GC\n"
            f"Proposed Total Duration: {proposal.proposed_duration or 'N/A'}\n"
            f"Cover Letter: {proposal.cover_letter or 'N/A'}\n"
            f"Analysis Summary: {proposal.analysis_summary or 'N/A'}\n"
            f"Solution Approach: {proposal.solution_approach or 'N/A'}\n"
            f"Freelancer Edited Milestones:\n{edited_ms_block}\n\n"
            f"Vetting Screening Q&A Responses:\n{qa_block}\n\n"
            "Perform structured qualitative evaluation and evidence extraction."
        )

        try:
            raw_response = await self.llm.generate(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_format=LLMQualitativeEvaluation,
            )

            llm_eval = self._parse_llm_evaluation(raw_response)
        except Exception as exc:
            logger.exception(f"LLM qualitative generation failed for proposal {proposal.proposal_id}: {exc}")
            llm_eval = self._create_fallback_evaluation(proposal)

        # Execute deterministic calculation
        deterministic = DeterministicCalculator.calculate(llm_eval, baseline, proposal)

        return CandidateJudgingResponse(
            proposal_id=proposal.proposal_id,
            job_id=baseline.job_id,
            llm_qualitative_evaluation=llm_eval,
            deterministic_calculations=deterministic,
        )

    async def evaluate_batch(
        self, request: BatchCandidateJudgingRequest
    ) -> BatchCandidateJudgingResponse:
        """Evaluate a batch of candidate proposals in chunked parallel executions."""
        proposals = request.proposals
        chunk_size = max(1, min(5, request.batch_chunk_size))
        judged_proposals: List[CandidateJudgingResponse] = []

        for i in range(0, len(proposals), chunk_size):
            chunk = proposals[i : i + chunk_size]
            tasks = [
                self.evaluate_candidate(
                    CandidateJudgingRequest(
                        job_post_baseline=request.job_post_baseline,
                        candidate_proposal=p,
                    )
                )
                for p in chunk
            ]
            chunk_results = await asyncio.gather(*tasks, return_exceptions=True)
            for res in chunk_results:
                if isinstance(res, CandidateJudgingResponse):
                    judged_proposals.append(res)
                elif isinstance(res, Exception):
                    logger.error(f"Batch candidate judging chunk error: {res}")

        return BatchCandidateJudgingResponse(
            processed_count=len(judged_proposals),
            total_requested=len(proposals),
            is_completed=len(judged_proposals) == len(proposals),
            judged_proposals=judged_proposals,
        )

    def _parse_llm_evaluation(self, raw_text: str) -> LLMQualitativeEvaluation:
        """Parse raw LLM output string into LLMQualitativeEvaluation Pydantic model."""
        if not raw_text or not isinstance(raw_text, str):
            raise ValueError("Empty LLM response string")

        try:
            return LLMQualitativeEvaluation.model_validate_json(raw_text)
        except (ValidationError, ValueError, TypeError):
            start = raw_text.find("{")
            end = raw_text.rfind("}")
            if start >= 0 and end > start:
                try:
                    return LLMQualitativeEvaluation.model_validate_json(
                        raw_text[start : end + 1]
                    )
                except (ValidationError, ValueError, TypeError) as exc:
                    logger.warning(f"Failed substring JSON extraction: {exc}")

            raise ValueError("Could not parse LLM output as LLMQualitativeEvaluation JSON")

    def _create_fallback_evaluation(
        self, proposal: ProposalOfferDto
    ) -> LLMQualitativeEvaluation:
        """Provide structured fallback when LLM provider fails."""
        from app.schemas.candidate_judging_schemas import (
            SubcriteriaScoreWithEvidence,
            EvidenceClaim,
            TechnicalSolutionQualitativeEval,
            QuestionAnswerQualitativeEval,
            RequirementFulfillmentItem,
        )

        default_subscore = SubcriteriaScoreWithEvidence(
            score=70.0,
            evidence=[
                EvidenceClaim(
                    claim="Standard proposal submitted",
                    source="proposal.solutionApproach",
                    assessment="Feasible",
                )
            ],
        )

        qa_evals = []
        for qa in proposal.vetting_qa_answers:
            qa_evals.append(
                QuestionAnswerQualitativeEval(
                    question_index=qa.question_index,
                    question_text=qa.question_text,
                    candidate_answer=qa.candidate_answer,
                    answer_correctness=default_subscore,
                    technical_reasoning=default_subscore,
                    relevance=default_subscore,
                    depth=default_subscore,
                    practical_examples=default_subscore,
                )
            )

        return LLMQualitativeEvaluation(
            technical_solution=TechnicalSolutionQualitativeEval(
                requirement_alignment=default_subscore,
                technical_correctness=default_subscore,
                architecture_quality=default_subscore,
                implementation_feasibility=default_subscore,
                edge_cases_security=default_subscore,
            ),
            screening_qa=qa_evals,
            requirement_fulfillment=[
                RequirementFulfillmentItem(
                    requirement="Core deliverables",
                    is_fulfilled=True,
                    matched_milestone="Edited Milestones",
                    note="Assumed fulfilled in fallback",
                )
            ],
            pricing_realism=default_subscore,
            timeline_feasibility=default_subscore,
            milestone_structure=default_subscore,
            project_specificity=default_subscore,
            substance_density=default_subscore,
            probing_questions=["Could you elaborate on your proposed architecture details?"],
        )


_candidate_judging_service: Optional[CandidateJudgingService] = None


def get_candidate_judging_service() -> CandidateJudgingService:
    global _candidate_judging_service
    if _candidate_judging_service is None:
        _candidate_judging_service = CandidateJudgingService()
    return _candidate_judging_service
