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
            "You are an expert AI Evaluator and Hiring Judge for GigBridge, a freelance marketplace for ALL professional domains (Software Engineering, UI/UX Design, Digital Marketing, Copywriting, Video Production, Finance/Accounting, Consulting, etc.).\n"
            "Evaluate the candidate's proposal offer and screening Q&A answers strictly against the specific client job post baseline requirements.\n\n"
            "DYNAMIC FAIRNESS & MULTI-PROFESSION DOMAIN RULE:\n"
            "- Dynamically adapt technical, design, marketing, or professional evaluation criteria based on the specific job domain.\n"
            "- DO NOT hardcode specific tools or technologies as mandatory unless explicitly required in THIS job post.\n"
            "- Evaluate candidate responses strictly against the explicit constraints, required skills, and deliverables of THIS specific job post.\n\n"
            "STRICT GROUND TRUTH COMPARISON & ANTI-HALLUCINATION GUARDRAILS:\n"
            "- NEVER award passing or high scores to generic fluff, lazy promises ('Hire me I am expert'), or copy-pasted boilerplate.\n"
            "- CRITICAL RULE - UNRELATED / OFF-TOPIC RESPONSES: If candidate's proposal or answer is UNRELATED to the job post (e.g. discussing mobile apps for a graphic design job, selling unrelated products, or off-topic text), ALL Pillar 1 sub-criteria MUST be capped at 0 to 15 / 100.\n"
            "- CRITICAL RULE - GENERIC FLUFF / TRASH RESPONSES: If the proposal contains generic filler ('I am passionate developer, I will finish fast') without naming specific tools, workflows, or deliverables tailored to THIS job post, ALL Pillar 1 sub-criteria MUST be capped at 16 to 30 / 100.\n"
            "- Concise 1-3 sentence answers providing exact domain facts and tailored steps score HIGHER than wordy 500-word generic essays.\n\n"
            "4-PILLAR EVALUATION PROMPT CONTROL SUITE:\n"
            "1. PILLAR 1 - SOLUTION & DELIVERY METHODOLOGY (35% Weight):\n"
            "   Evaluate candidate's proposed solution approach across 5 explicit sub-criteria (each 0-100), comparing STRICTLY against THIS Job Description:\n"
            "   a) REQUIREMENT ALIGNMENT (requirement_alignment, 30% weight): Does the proposed stack/toolset/approach explicitly align with or enhance the job description's stated needs?\n"
            "   b) METHODOLOGICAL & TECHNICAL CORRECTNESS (technical_correctness, 25% weight): Are the proposed techniques, processes, or engineering/design/marketing patterns technically sound and appropriate for this specific job problem? (Cap < 20 for unrelated or flawed logic).\n"
            "   c) SOLUTION & WORKFLOW ARCHITECTURE (architecture_quality, 20% weight): Is the solution structure, process workflow, deliverable breakdown, database/system/design structure clear, logical, and tailored to the job's scope? (Cap < 25 if no specific workflow or architecture is described).\n"
            "   d) PRACTICAL FEASIBILITY (implementation_feasibility, 15% weight): Are the proposed execution steps, tools, and timelines realistic and executable for this specific project?\n"
            "   e) RISK MITIGATION & QUALITY CONTROL (edge_cases_security, 10% weight): Does the candidate identify project-specific risks, quality control steps, testing/review protocols, or security/edge cases relevant to the job domain? (Cap < 20 if unmentioned).\n"
            "2. PILLAR 2 - VETTING SCREENING Q&A ACCURACY & REASONING (30% Weight):\n"
            "   Evaluate candidate's screening answers across 5 explicit sub-criteria (each 0-100):\n"
            "   a) ANSWER CORRECTNESS (answer_correctness, 40% weight): Factual accuracy, absence of hallucinations, and correctness of core concepts.\n"
            "   b) REASONING & LOGIC (technical_reasoning, 25% weight): Depth of problem-solving logic, trade-off justification, and professional rationale.\n"
            "   c) RELEVANCE (relevance, 15% weight): Directness in answering the exact question asked without off-topic tangents.\n"
            "   d) DOMAIN DEPTH (depth, 10% weight): Specificity of technical/professional mechanics vs generic high-level statements.\n"
            "   e) PRACTICAL EXAMPLES (practical_examples, 10% weight): Inclusion of concrete workflow patterns, past experience details, or realistic scenario handling.\n"
            "   - STRICT Q&A COUNT CONSTRAINT: Output EXACTLY ONE item in `screening_qa` array for each question explicitly provided in 'Vetting Screening Q&A Responses'. If 0 questions are provided, output `[]`.\n"
            "   - AI-GENERATED ANSWER & AUTHENTICITY DETECTION GUARDRAIL:\n"
            "     * Actively detect whether candidate answer exhibits stereotypical AI generator signatures (e.g. ChatGPT intro phrases like 'The process usually works like this:', uniform numbered lists with bold lead-ins, generic ungrounded fluff).\n"
            "     * If AI generator patterns are detected, set `is_ai_generated: true` and specify `ai_detection_reason`.\n"
            "     * Heavy copy-pasted AI textbook answers MUST be penalized on `depth` and `practical_examples` sub-criteria (scores < 60).\n"
            "   - ANTI-VERBOSITY RULE: Apply a verbosity penalty (score < 40) for padded fluff or generic filler phrases.\n"
            "3. PILLAR 3 - PRICING REALISM & TIMELINE FEASIBILITY (20% Weight):\n"
            "   - PRICING REALISM (pricing_realism score 0-100): Evaluate proposed total budget and milestone prices against scope complexity. Penalize suspicious underbidding (< 50% fair rate) as quality traps (score < 50). Penalize excessive price gouging. Reward fair milestone pricing (score 80-100).\n"
            "   - TIMELINE FEASIBILITY (timeline_feasibility score 0-100): Evaluate milestone durations against standard professional velocity. Penalize impossible rush promises (e.g. 1 day for multi-page complex project) as reckless commitments (score < 50).\n"
            "4. PILLAR 4 - MILESTONE SCOPE & DELIVERABLES (15% Weight):\n"
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
            score=35.0,
            evidence=[
                EvidenceClaim(
                    claim="Fallback evaluation triggered - LLM evaluation service unavailable",
                    source="proposal.solutionApproach",
                    assessment="Unclear",
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
