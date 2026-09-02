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

        # Resolve canonical baseline budget_max and estimated_duration from original_milestones if header properties are null/0/empty
        if (not baseline.budget_max or baseline.budget_max <= 0) and baseline.original_milestones:
            ms_sum = sum(m.amount for m in baseline.original_milestones if m.amount)
            if ms_sum > 0:
                baseline.budget_max = ms_sum
            elif baseline.budget_min and baseline.budget_min > 0:
                baseline.budget_max = baseline.budget_min
        elif (not baseline.budget_max or baseline.budget_max <= 0) and baseline.budget_min and baseline.budget_min > 0:
            baseline.budget_max = baseline.budget_min

        if not baseline.estimated_duration or baseline.estimated_duration in ("—", "null"):
            if baseline.original_milestones:
                durations = [m.estimated_duration for m in baseline.original_milestones if m.estimated_duration and m.estimated_duration not in ("—", "null")]
                if durations:
                    baseline.estimated_duration = " + ".join(durations)

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
            "   - STRICT TECHNICAL DEPTH & REASONING GUARDRAIL FOR GENERIC ANSWERS:\n"
            "     * High-level, surface-level, or generic textbook responses (e.g. 'understanding target audience, brand guidelines, consistent & scalable system') without naming specific tools, design tokens, architecture specs, step-by-step technical implementation, or trade-offs MUST BE STRICTLY PENALIZED.\n"
            "     * For generic/high-level answers lacking concrete technical tools/artifacts: CAP `technical_reasoning` AT 40-55 / 100 max, CAP `depth` AT 30-50 / 100 max, and CAP `practical_examples` AT 30-50 / 100 max.\n"
            "     * DO NOT award scores > 75 for `technical_reasoning` or `depth` unless the candidate names specific domain tools/artifacts (e.g. Figma design systems, tokens, CSS/component frameworks, specific API tools, database schemas) and provides practical trade-off logic.\n"
            "   - STRICT Q&A COUNT CONSTRAINT: Output EXACTLY ONE item in `screening_qa` array for each question explicitly provided in 'Vetting Screening Q&A Responses'. If 0 questions are provided, output `[]`.\n"
            "   - AI-GENERATED ANSWER & AUTHENTICITY DETECTION GUARDRAIL:\n"
            "     * Actively detect whether candidate answer exhibits stereotypical AI generator signatures (e.g. ChatGPT intro phrases like 'The process usually works like this:', uniform numbered lists with bold lead-ins, generic ungrounded fluff).\n"
            "     * If AI generator patterns are detected, set `is_ai_generated: true` and specify `ai_detection_reason`.\n"
            "     * Heavy copy-pasted AI textbook answers MUST be penalized on `depth` and `practical_examples` sub-criteria (scores < 60).\n"
            "   - FACTUAL & EXPERIENCE QUESTION SCORING GUARDRAIL:\n"
            "     * Actively detect whether a screening question is a factual, experience, or numerical qualification question (e.g. asking for years of experience, rate, availability, or certifications like 'How many years of experience do you have for this role?').\n"
            "     * For factual/experience questions, compare stated candidate answer directly against job description requirements.\n"
            "     * If stated metrics meet or exceed job requirements (e.g. candidate states '3 years' or '5 years' when job requires 3+ years), DO NOT penalize for lacking multi-paragraph code essays or trade-off reasoning.\n"
            "     * For valid factual answers meeting job criteria, assign 100/100 across answer_correctness, technical_reasoning, relevance, depth, and practical_examples (yielding 100/100 overall question score).\n"
            "     * If stated experience falls below job requirements (e.g. 1 year vs 3 required), scale score down proportionally (e.g. score < 40).\n"
            "   - ANTI-VERBOSITY RULE: Apply a verbosity penalty (score < 40) for padded fluff or generic filler phrases.\n"
            "3. PILLAR 3 - FINANCIAL & PRICING VALUE (20% Weight - Pure Financial):\n"
            "   - PRICING REALISM ONLY (pricing_realism score 0-100): Evaluate proposed total budget and milestone prices against scope complexity. Penalize suspicious underbidding (< 50% fair market rate) as quality traps (score < 50). Penalize excessive price gouging. Reward fair, market-aligned milestone pricing (score 80-100). DO NOT evaluate project duration or timeline in Pillar 3.\n"
            "4. PILLAR 4 - MILESTONE SCOPE, DELIVERABLES & TIMELINE FEASIBILITY (15% Weight):\n"
            "   - MILESTONE DELTA AUDIT (milestone_audit array):\n"
            "     * Compare client baseline milestones against freelancer's edited milestones across ALL 4 attributes: Title, Budget/Amount, Duration, and Description/Deliverables.\n"
            "     * For EACH candidate milestone (and any deleted baseline milestone), classify `status` as EXACTLY ONE OF:\n"
            "       - 'Preserved': Milestone is completely unchanged (same title, budget, duration, and description).\n"
            "       - 'Edited': Freelancer customized Title, Budget (Amount), Duration, or Description/Deliverables.\n"
            "       - 'Added': Freelancer introduced a new custom milestone phase.\n"
            "       - 'Deleted': Baseline milestone was removed/omitted by freelancer.\n"
            "     * Provide a precise `change_summary` specifying EXACTLY which of the 4 attributes were modified (e.g. 'Điều chỉnh: Chi phí (1,000 → 1,200 GC), Thời gian (1 tuần → 2 tuần), Mô tả / Sản phẩm bàn giao').\n"
            "   - REQUIREMENT SCOPE FULFILLMENT (requirement_fulfillment array):\n"
            "     * Extract ONLY concrete, functional project deliverables & feature requirements from the job post.\n"
            "     * STRICT ANTI-HALLUCINATION RULE: DO NOT extract developer background qualifications, years of experience, or general skill requirements (e.g., 'Proven experience with FastAPI and Python') into `requirement_fulfillment`.\n"
            "     * Evaluate SEMANTIC fulfillment across BOTH the candidate's solution approach AND edited milestones combined.\n"
            "     * Mark `is_fulfilled: true` ONLY if the candidate's offer semantically covers the feature deliverable with valid technical details.\n"
            "     * STRICT QUALITY & FLUFF GUARDRAIL: DO NOT mark `is_fulfilled: true` if the candidate's response is generic fluff, off-topic, or lacks tailored technical details for that deliverable.\n"
            "     * VERIFIABLE EVIDENCE PROOF REQUIREMENT: For EVERY item in `requirement_fulfillment`, populate `evidence_quote` with the exact sentence quote or phrase from the candidate's solution approach, cover letter, or milestone description proving coverage. If unfulfilled (`is_fulfilled: false`), specify the exact gap quote or reason.\n"
            "     * DO NOT penalize or mark deliverables as unfulfilled merely because milestone titles are renamed, edited, or restructured by the freelancer.\n"
            "   - MILESTONE STRUCTURE & GRANULARITY (30% weight): Reward clear, granular milestone titles with verifiable deliverables; penalize vague single-blob milestones (milestone_structure score 0-100).\n"
            "   - TIMELINE FEASIBILITY & DURATION REALISM (30% weight): Evaluate proposed milestone durations against standard professional velocity (timeline_feasibility score 0-100). Penalize impossible rush promises (e.g. 1 day for multi-page complex project) as reckless commitments (score < 50).\n\n"
            "STRICT JOB DESCRIPTION BASELINE LANGUAGE CORRESPONDENCE RULE:\n"
            "- CRITICAL: Output ALL qualitative evaluation text fields (`requirement_fulfillment` requirement titles, `screening_qa` feedback, `pillar_comments`, `answer_quality_summary_comment`, and `probing_questions`) strictly in the PRIMARY LANGUAGE of the JOB DESCRIPTION BASELINE.\n"
            "- If the Job Description baseline is written in VIETNAMESE, output ALL `requirement` titles, `screening_qa` feedback, `pillar_comments`, `answer_quality_summary_comment`, and `probing_questions` in clear, professional VIETNAMESE (even if the candidate proposal is written in English).\n"
            "- If the Job Description baseline is written in ENGLISH, output ALL `requirement` titles, `screening_qa` feedback, `pillar_comments`, `answer_quality_summary_comment`, and `probing_questions` in clear, professional ENGLISH (even if the candidate proposal is written in Vietnamese).\n"
            "- CRITICAL EVIDENCE EXPLICIT QUOTE RULE: For `evidence_quote` in `requirement_fulfillment`, extract the EXACT sentence/phrase directly from the candidate's proposal text in the candidate's language so that the frontend can pinpoint exact character highlight ranges.\n\n"
            "PILLAR COMMENT EXPLANATIONS REQUIREMENT:\n"
            "- PER-SUBCRITERIA BREAKDOWN REQUIREMENT: For EACH of the 4 pillars in `pillar_comments`, provide a structured breakdown explaining WHY the candidate received that score for EACH individual sub-criterion:\n"
            "  * technical_solution: Explain 1) Requirement Alignment (25%), 2) Problem Analysis (25%), 3) Solution Architecture (25%), 4) Deliverables (15%), and 5) Scope Boundaries (10%).\n"
            "  * screening_qa: Explain 1) Correctness (40%), 2) Technical Reasoning (25%), 3) Relevance (15%), 4) Depth (10%), and 5) Practical Examples (10%). If 0 screening questions were answered, explicitly state that 0 questions were answered.\n"
            "  * financial_value: Explain 1) Pricing Realism (50%) and 2) Budget Savings (50%). If proposed price equals client budget cap, explicitly state that candidate offer remains unchanged from the baseline budget, providing 0% cost savings.\n"
            "  * milestone_scope: Explain 1) Scope Completeness % (40%), 2) Milestone Structure Granularity (30%), and 3) Timeline Duration Feasibility (30%).\n\n"
            "EVIDENCE TRACE REQUIREMENT:\n"
            "- For EVERY subcriteria score (0-100), extract concrete evidence claims from the proposal/answers.\n"
            "- Include exact claim text, source field location (e.g. 'proposal.solutionApproach', 'answer_1'), and assessment ('Correct', 'Incorrect', 'Partial', 'Feasible', 'Unclear').\n\n"
            "SINGLE AI SUMMARY COMMENT REQUIREMENT:\n"
            "- Output a SINGLE comprehensive qualitative summary comment in `answer_quality_summary_comment`.\n"
            "- For strong answers: Provide a detailed compliment highlighting technical methodology strengths.\n"
            "- For vague/generic/AI-generated answers: Provide a detailed complaint explaining specific fluff/vague phrasing or AI boilerplate signatures.\n"
            "- DO NOT output 2-3 disjointed or redundant comments.\n\n"
            "PROBING QUESTIONS & TECHNICAL CLARIFICATION REQUIREMENT:\n"
            "- Output 2-3 specific technical clarification questions in `probing_questions` array.\n"
            "- Format EACH item in `probing_questions` strictly starting with 'Problem #1: ...', 'Problem #2: ...', etc.\n"
            "- Focus explicitly on specific technical gaps, unmentioned architecture tools, missing scope boundaries, or trade-off items that the candidate must clarify in the interview.\n\n"
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

        # Enforce complete milestone delta audit (Preserved, Edited, Added, Deleted)
        llm_eval = self._sanitize_milestone_audit(llm_eval, baseline, proposal)

        # Execute deterministic calculation
        deterministic = DeterministicCalculator.calculate(llm_eval, baseline, proposal)

        return CandidateJudgingResponse(
            proposal_id=proposal.proposal_id,
            job_id=baseline.job_id,
            job_post_baseline=baseline,
            proposal_offer=proposal,
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
        used_eval_indices = set()

        for idx, input_qa in enumerate(input_qa_list, start=1):
            input_idx = input_qa.question_index if input_qa.question_index is not None else idx

            # Find matching item in LLM screening_qa output by input index or position
            matching_eval = None
            for eval_idx, eval_item in enumerate(llm_eval.screening_qa):
                if eval_idx in used_eval_indices:
                    continue
                if eval_item.question_index == input_idx or eval_item.question_index == idx:
                    matching_eval = eval_item
                    used_eval_indices.add(eval_idx)
                    break

            # Fallback to positional order if index match fails
            if not matching_eval:
                for eval_idx, eval_item in enumerate(llm_eval.screening_qa):
                    if eval_idx not in used_eval_indices:
                        matching_eval = eval_item
                        used_eval_indices.add(eval_idx)
                        break

            if matching_eval:
                # Copy exact ground-truth question text, candidate answer, and sequential 1-based index (idx)
                eval_copy = matching_eval.model_copy(deep=True)
                eval_copy.question_index = idx
                eval_copy.question_text = input_qa.question_text
                eval_copy.candidate_answer = input_qa.candidate_answer
                sanitized_qa.append(eval_copy)

        llm_eval.screening_qa = sanitized_qa
        return llm_eval

    def _sanitize_milestone_audit(
        self,
        llm_eval: LLMQualitativeEvaluation,
        baseline: JobPostBaselineDto,
        proposal: ProposalOfferDto,
    ) -> LLMQualitativeEvaluation:
        """Enforce complete milestone delta audit across all 4 statuses: Preserved, Edited, Added, Deleted."""
        from app.schemas.candidate_judging_schemas import MilestoneAuditItem

        orig_milestones = baseline.original_milestones or []
        edited_milestones = proposal.edited_milestones or []

        existing_audits = llm_eval.milestone_audit or []
        audit_by_title = {
            a.milestone_title.strip().lower(): a for a in existing_audits if a.milestone_title
        }

        sanitized_audits: List[MilestoneAuditItem] = []

        # 1. Process candidate proposed milestones first
        for idx, ms in enumerate(edited_milestones, start=1):
            ms_title_lower = ms.title.strip().lower() if ms.title else ""

            # Find matching original baseline milestone by title
            matched_orig = next(
                (o for o in orig_milestones if o.title and (o.title.strip().lower() == ms_title_lower or ms_title_lower in o.title.strip().lower() or o.title.strip().lower() in ms_title_lower)),
                None
            )

            existing_item = audit_by_title.get(ms_title_lower)
            if not existing_item:
                existing_item = next((a for a in existing_audits if a.order_index == idx), None)

            if matched_orig:
                is_price_changed = abs((matched_orig.amount or 0.0) - (ms.amount or 0.0)) > 0.01
                is_dur_changed = (matched_orig.estimated_duration or "").strip() != (ms.estimated_duration or "").strip()
                is_title_changed = (matched_orig.title or "").strip().lower() != (ms.title or "").strip().lower()
                
                orig_desc = (matched_orig.description or matched_orig.deliverables or "").strip()
                ms_desc = (ms.description or ms.deliverables or "").strip()
                is_desc_changed = bool(orig_desc or ms_desc) and (orig_desc != ms_desc)

                modified_fields = []
                if is_title_changed:
                    modified_fields.append(f"Tiêu đề: '{matched_orig.title}' → '{ms.title}'")
                if is_price_changed:
                    modified_fields.append(f"Chi phí: {matched_orig.amount:,.0f} → {ms.amount:,.0f} GC")
                if is_dur_changed:
                    modified_fields.append(f"Thời gian: '{matched_orig.estimated_duration or 'N/A'}' → '{ms.estimated_duration or 'N/A'}'")
                if is_desc_changed:
                    modified_fields.append("Mô tả / sản phẩm bàn giao đã được điều chỉnh")

                is_modified = len(modified_fields) > 0

                if is_modified:
                    status = "Edited"
                    change_summary = f"Điều chỉnh: {', '.join(modified_fields)}"
                elif existing_item and existing_item.status in ("Preserved", "Edited"):
                    status = existing_item.status
                    change_summary = existing_item.change_summary or "Baseline milestone preserved"
                else:
                    status = "Preserved"
                    change_summary = "Baseline milestone preserved"

                sanitized_audits.append(
                    MilestoneAuditItem(
                        order_index=ms.order_index if ms.order_index else idx,
                        milestone_title=ms.title,
                        status=status,
                        change_summary=change_summary,
                        is_scope_covered=True,
                    )
                )
            else:
                sanitized_audits.append(
                    MilestoneAuditItem(
                        order_index=ms.order_index if ms.order_index else idx,
                        milestone_title=ms.title,
                        status="Added",
                        change_summary=existing_item.change_summary if existing_item else "Freelancer proposed custom new milestone phase",
                        is_scope_covered=True,
                    )
                )

        # 2. Identify missing original baseline milestones (Deleted)
        for orig_idx, orig_ms in enumerate(orig_milestones, start=1):
            orig_title_lower = orig_ms.title.strip().lower() if orig_ms.title else ""
            matched_candidate = next(
                (m for m in edited_milestones if m.title and (m.title.strip().lower() == orig_title_lower or orig_title_lower in m.title.strip().lower() or m.title.strip().lower() in orig_title_lower)),
                None
            )

            if not matched_candidate:
                existing_del = next(
                    (a for a in existing_audits if a.milestone_title and a.milestone_title.strip().lower() == orig_title_lower and a.status == "Deleted"),
                    None
                )

                change_summary = (
                    existing_del.change_summary
                    if existing_del and existing_del.change_summary
                    else f"Baseline milestone '{orig_ms.title}' omitted by freelancer"
                )

                sanitized_audits.append(
                    MilestoneAuditItem(
                        order_index=orig_ms.order_index if orig_ms.order_index else (len(edited_milestones) + orig_idx),
                        milestone_title=orig_ms.title,
                        status="Deleted",
                        change_summary=change_summary,
                        is_scope_covered=False,
                    )
                )

        llm_eval.milestone_audit = sanitized_audits
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
            MilestoneAuditItem,
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

        ms_audits = [
            MilestoneAuditItem(
                order_index=ms.order_index,
                milestone_title=ms.title,
                status="Edited",
                change_summary="Freelancer proposed milestone",
                is_scope_covered=True,
            )
            for ms in proposal.edited_milestones
        ] if proposal.edited_milestones else []

        return LLMQualitativeEvaluation(
            technical_solution=TechnicalSolutionQualitativeEval(
                requirement_alignment=default_subscore,
                technical_correctness=default_subscore,
                architecture_quality=default_subscore,
                implementation_feasibility=default_subscore,
                edge_cases_security=default_subscore,
            ),
            screening_qa=qa_evals,
            milestone_audit=ms_audits,
            requirement_fulfillment=[
                RequirementFulfillmentItem(
                    requirement="Core deliverables",
                    is_fulfilled=False,
                    matched_milestone="Edited Milestones",
                    evidence_quote="Unverified - Fallback evaluation triggered due to LLM provider error.",
                    note="Unfulfilled in fallback assessment",
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
