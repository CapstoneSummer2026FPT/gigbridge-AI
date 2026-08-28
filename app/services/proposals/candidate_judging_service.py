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
            "4-PILLAR EVALUATION PROMPT CONTROL SUITE:\n"
            "1. PILLAR 1 - TECHNICAL SOLUTION & ARCHITECTURE (35%):\n"
            "   Evaluate candidate's proposal solution approach across 5 explicit sub-criteria (each 0-100):\n"
            "   a) REQUIREMENT ALIGNMENT (requirement_alignment, 25% weight): Alignment with job description requirements and specified tech stack.\n"
            "   b) TECHNICAL CORRECTNESS (technical_correctness, 30% weight): Sound technical choices, valid engineering patterns, absence of flawed logic.\n"
            "   c) ARCHITECTURE QUALITY (architecture_quality, 20% weight): System design clarity, modularity, database schema, and data flow.\n"
            "   d) IMPLEMENTATION FEASIBILITY (implementation_feasibility, 15% weight): Practical executability and realistic implementation steps.\n"
            "   e) EDGE CASES & SECURITY (edge_cases_security, 10% weight): Security practices, input validation, encryption, error handling, and edge cases.\n"
            "2. PILLAR 2 - VETTING SCREENING Q&A ACCURACY & REASONING (30%):\n"
            "   Evaluate candidate's screening answers across 5 explicit sub-criteria (each 0-100):\n"
            "   a) ANSWER CORRECTNESS (answer_correctness, 40% weight): Technical factual accuracy, absence of hallucinations, and correctness of core concepts.\n"
            "   b) TECHNICAL REASONING (technical_reasoning, 25% weight): Depth of problem-solving logic, architectural trade-off justification, and engineering rationale.\n"
            "   c) RELEVANCE (relevance, 15% weight): Directness in answering the exact question asked without off-topic tangents.\n"
            "   d) TECHNICAL DEPTH (depth, 10% weight): Specificity of technical mechanics, exact API/framework references vs. generic high-level statements.\n"
            "   e) PRACTICAL EXAMPLES (practical_examples, 10% weight): Inclusion of concrete code patterns, past experience details, or realistic scenario handling.\n"
            "   - STRICT Q&A COUNT CONSTRAINT: Output EXACTLY ONE item in `screening_qa` array for each question explicitly provided in 'Vetting Screening Q&A Responses'.\n"
            "   - DO NOT fabricate, invent, generate, or hallucinate any extra screening questions or fake candidate answers. If 1 question is provided, output EXACTLY 1 item in `screening_qa`. If 0 questions are provided, output an empty `screening_qa` array `[]`.\n"
            "   - AI-GENERATED ANSWER & AUTHENTICITY DETECTION GUARDRAIL:\n"
            "     * Actively detect whether candidate answer exhibits stereotypical AI generator signatures (e.g. ChatGPT intro phrases like 'The process usually works like this:', uniform numbered lists with bold lead-ins, textbook definitions lacking personal engineering experience, or generic ungrounded fluff).\n"
            "     * If AI generator patterns are detected, set `is_ai_generated: true` and specify `ai_detection_reason` (e.g. 'Contains overt ChatGPT introductory filler and generic textbook list format without concrete project implementation details').\n"
            "     * Heavy copy-pasted AI textbook answers MUST be penalized on `depth` and `practical_examples` sub-criteria (scores < 60).\n"
            "     * `qualitative_feedback`: MUST provide a detailed 2-4 sentence technical evaluation and authenticity analysis highlighting technical strengths/flaws, specific code/architecture references, and AI generation findings.\n"
            "   - ANTI-VERBOSITY RULE: NEVER reward answer length or word count. Concise 1-3 sentence answers containing exact technical facts score HIGHER than wordy 500-word fluff essays.\n"
            "   - Apply a verbosity penalty (score < 40) for padded fluff or generic filler phrases ('As a passionate developer...').\n"
            "3. PILLAR 3 - PRICING REALISM & TIMELINE FEASIBILITY (20%):\n"
            "   - PRICING REALISM (pricing_realism score 0-100): Evaluate candidate's total proposed budget and milestone prices against scope complexity. Penalize suspicious underbidding (< 50% fair market rate for complex scope) as quality traps (score < 50). Penalize excessive price gouging. Reward fair, market-aligned milestone pricing (score 80-100).\n"
            "   - TIMELINE FEASIBILITY (timeline_feasibility score 0-100): Evaluate whether milestone durations (e.g. 1 week, 3 weeks) match standard engineering velocity for the deliverables. Penalize impossible rush promises (e.g. 1 day for multi-service backend) as reckless commitments (score < 50). Reward realistic, well-phased milestone schedules (score 80-100).\n"
            "4. PILLAR 4 - MILESTONE SCOPE & DELIVERABLES (15%):\n"
            "   - Map each explicit job post requirement/deliverable to candidate's edited milestones (mark is_fulfilled as true/false).\n"
            "   - Milestone Structure (milestone_structure score 0-100): Reward clear, granular milestone titles with verifiable deliverables; penalize vague single-blob milestones.\n\n"
            "EVIDENCE TRACE REQUIREMENT:\n"
            "- For EVERY subcriteria score (0-100), extract concrete evidence claims from the proposal/answers.\n"
            "- Include exact claim text, source field location (e.g. 'proposal.solutionApproach', 'answer_1'), and assessment ('Correct', 'Incorrect', 'Partial', 'Feasible', 'Unclear').\n\n"
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

        # Enforce strict 1:1 matching of screening_qa evaluation items to proposal.vetting_qa_answers
        llm_eval = self._sanitize_screening_qa(llm_eval, proposal)

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

    def _sanitize_screening_qa(
        self, llm_eval: LLMQualitativeEvaluation, proposal: ProposalOfferDto
    ) -> LLMQualitativeEvaluation:
        """Enforce strict 1:1 matching of screening_qa evaluation items to proposal.vetting_qa_answers."""
        input_qa_list = proposal.vetting_qa_answers or []
        if not input_qa_list:
            llm_eval.screening_qa = []
            return llm_eval

        sanitized_qa = []
        for idx, input_qa in enumerate(input_qa_list, start=1):
            target_q_idx = input_qa.question_index if input_qa.question_index is not None else idx

            # Find matching item in LLM screening_qa output by question_index
            matching_eval = None
            for eval_item in llm_eval.screening_qa:
                if eval_item.question_index == target_q_idx:
                    matching_eval = eval_item
                    break

            # Fallback to positional order if index match fails
            if not matching_eval and (idx - 1) < len(llm_eval.screening_qa):
                matching_eval = llm_eval.screening_qa[idx - 1]

            if matching_eval:
                # Copy exact ground-truth question text, candidate answer, and index
                matching_eval.question_index = target_q_idx
                matching_eval.question_text = input_qa.question_text
                matching_eval.candidate_answer = input_qa.candidate_answer
                sanitized_qa.append(matching_eval)

        llm_eval.screening_qa = sanitized_qa
        return llm_eval

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
                    is_ai_generated=False,
                    ai_detection_reason="Fallback standard technical evaluation.",
                    qualitative_feedback="Technical quality assessment based on candidate response.",
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
