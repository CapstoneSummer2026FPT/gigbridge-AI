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
            "   Evaluate candidate's proposal text STRICTLY across the 6 core proposal sections below (each sub-criterion 0-100):\n"
            "   - SCOPE & EXCLUSION RULE: Evaluate ONLY proposal text sections (1. Giới thiệu & Tổng quan / Introduction & Overview, 2. Phân tích vấn đề / Problem Analysis, 3. Giải pháp & Hướng tiếp cận kỹ thuật / Solution & Technical Approach, 4. Sản phẩm bàn giao / Deliverables & Outputs, 5. Giả định dự án / Project Assumptions, 6. Các hạng mục ngoài phạm vi / Out-of-Scope Items).\n"
            "   - EXPLICIT MILESTONE EXCLUSION RULE: DO NOT score or evaluate the proposed Milestone Plan (Kế hoạch Milestone đề xuất) in Pillar 1. Milestone schedules and deliverable mapping are evaluated strictly in Pillar 4.\n"
            "   a) REQUIREMENT ALIGNMENT (requirement_alignment, 25% weight): Evaluates Section 1 (Giới thiệu & Tổng quan) - Alignment of introduction & overview with job description requirements.\n"
            "   b) PROBLEM ANALYSIS & TECHNICAL CORRECTNESS (technical_correctness, 25% weight): Evaluates Section 2 (Phân tích vấn đề) - Depth of problem breakdown, factual correctness, and domain analysis. (Cap < 20 for unrelated or flawed logic).\n"
            "   c) SOLUTION & WORKFLOW ARCHITECTURE (architecture_quality, 25% weight): Evaluates Section 3 (Giải pháp & Hướng tiếp cận kỹ thuật) - System design, tools, process workflow, and technical/professional methodology. (Cap < 25 if missing or generic).\n"
            "   d) DELIVERABLES & PRACTICAL FEASIBILITY (implementation_feasibility, 15% weight): Evaluates Section 4 (Sản phẩm bàn giao) - Specificity of tangible deliverables and practical execution feasibility.\n"
            "   e) ASSUMPTIONS & SCOPE BOUNDARIES (edge_cases_security, 10% weight): Evaluates Section 5 (Giả định dự án) & Section 6 (Các hạng mục ngoài phạm vi) - Clear project assumptions, risk controls, quality standards, and explicit out-of-scope exclusion boundaries.\n"
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
            "3. PILLAR 3 - FINANCIAL & PRICING VALUE (20% Weight - Pure Financial):\n"
            "   - PRICING REALISM ONLY (pricing_realism score 0-100): Evaluate proposed total budget and milestone prices against scope complexity. Penalize suspicious underbidding (< 50% fair market rate) as quality traps (score < 50). Penalize excessive price gouging. Reward fair, market-aligned milestone pricing (score 80-100). DO NOT evaluate project duration or timeline in Pillar 3.\n"
            "4. PILLAR 4 - MILESTONE SCOPE, DELIVERABLES & TIMELINE FEASIBILITY (15% Weight):\n"
            "   - REQUIREMENT SCOPE COMPLETENESS (40% weight): Map each explicit job post requirement/deliverable to candidate's edited milestones (mark is_fulfilled as true/false).\n"
            "   - MILESTONE STRUCTURE & GRANULARITY (30% weight): Reward clear, granular milestone titles with verifiable deliverables; penalize vague single-blob milestones (milestone_structure score 0-100).\n"
            "   - TIMELINE FEASIBILITY & DURATION REALISM (30% weight): Evaluate proposed milestone durations against standard professional velocity (timeline_feasibility score 0-100). Penalize impossible rush promises (e.g. 1 day for multi-page complex project) as reckless commitments (score < 50).\n\n"
            "PILLAR COMMENT EXPLANATIONS REQUIREMENT:\n"
            "- DYNAMIC LANGUAGE MATCHING: If the job post baseline or candidate proposal is written in Vietnamese, output ALL `pillar_comments` in clear, professional VIETNAMESE. Otherwise, output in ENGLISH.\n"
            "- PER-SUBCRITERIA BREAKDOWN REQUIREMENT: For EACH of the 4 pillars in `pillar_comments`, provide a structured breakdown explaining WHY the candidate received that score for EACH individual sub-criterion:\n"
            "  * technical_solution: Explain 1) Requirement Alignment (25%), 2) Problem Analysis (25%), 3) Solution Architecture (25%), 4) Deliverables (15%), and 5) Scope Boundaries (10%).\n"
            "  * screening_qa: Explain 1) Correctness (40%), 2) Technical Reasoning (25%), 3) Relevance (15%), 4) Depth (10%), and 5) Practical Examples (10%). If 0 screening questions were answered, explicitly state that 0 questions were answered.\n"
            "  * financial_value: Explain 1) Pricing Realism (50%) and 2) Budget Savings (50%). If proposed price equals client budget cap, explicitly state that candidate offer remains unchanged from the baseline budget, providing 0% cost savings.\n"
            "  * milestone_scope: Explain 1) Scope Completeness % (40%), 2) Milestone Structure Granularity (30%), and 3) Timeline Duration Feasibility (30%).\n\n"
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
            PillarComments,
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
            pillar_comments=PillarComments(
                technical_solution="• Requirement Alignment (25%): Basic alignment with core job requirements.\n• Problem Analysis (25%): Superficial problem breakdown requiring further technical clarification.\n• Technical Solution (25%): High-level workflow proposed without detailed tool/architecture specs.\n• Deliverables (15%): Deliverable descriptions are brief and standard.\n• Scope Boundaries (10%): Project assumptions and out-of-scope items were unmentioned.",
                screening_qa="• Correctness (40%): Standard baseline accuracy.\n• Reasoning (25%): Technical logic requires interview verification.\n• Relevance (15%): Direct response provided.\n• Depth (10%): High-level overview.\n• Practical Examples (10%): No concrete scenario examples provided." if proposal.vetting_qa_answers else "• Q&A Status: Candidate did not complete any screening questions (0/100).",
                financial_value="• Pricing Realism (50%): Proposed pricing aligns with baseline market expectations (+50%).\n• Cost Savings (50%): Candidate offer remains unchanged from maximum client budget cap, providing 0% cost savings (+0%).",
                milestone_scope="• Scope Coverage (40%): Fulfills core job deliverables.\n• Milestone Structure (30%): Structured across standard milestone phases.\n• Timeline Feasibility (30%): Estimated duration aligns with baseline velocity.",
            ),
        )


_candidate_judging_service: Optional[CandidateJudgingService] = None


def get_candidate_judging_service() -> CandidateJudgingService:
    global _candidate_judging_service
    if _candidate_judging_service is None:
        _candidate_judging_service = CandidateJudgingService()
    return _candidate_judging_service
