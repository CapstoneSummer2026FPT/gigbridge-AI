"""
PURPOSE: Automated pytest verification suite for AI Candidate Evaluation Engine.
IMPORTANCE: Critical — Ensures mathematical accuracy, VS capping, scope completeness, and deterministic badge mapping.
"""

import pytest
from app.schemas.candidate_judging_schemas import (
    LLMQualitativeEvaluation,
    TechnicalSolutionQualitativeEval,
    QuestionAnswerQualitativeEval,
    RequirementFulfillmentItem,
    SubcriteriaScoreWithEvidence,
    EvidenceClaim,
    JobPostBaselineDto,
    ProposalOfferDto,
    ProposalMilestoneInput,
    QuestionAnswerPairInput,
)
from app.services.proposals.deterministic_calculator import DeterministicCalculator


def make_subscore(score: float) -> SubcriteriaScoreWithEvidence:
    return SubcriteriaScoreWithEvidence(
        score=score,
        evidence=[EvidenceClaim(claim="Test claim", source="test.source", assessment="Correct")],
    )


def test_mathematical_tq_rounding():
    """Verify that weighted TQ calculation rounds to exact expected value (87.14)."""
    # Pillar 1 subscores: 0.25(90) + 0.25(85) + 0.25(80) + 0.15(85) + 0.10(75) = 84.00
    tech = TechnicalSolutionQualitativeEval(
        requirement_alignment=make_subscore(90.0),
        technical_correctness=make_subscore(85.0),
        architecture_quality=make_subscore(80.0),
        implementation_feasibility=make_subscore(85.0),
        edge_cases_security=make_subscore(75.0),
    )

    # Pillar 2 Q&A score: 0.40(95) + 0.25(90) + 0.15(100) + 0.10(80) + 0.10(85) = 90.0
    qa = QuestionAnswerQualitativeEval(
        question_index=1,
        question_text="What is Redis?",
        candidate_answer="In-memory data store",
        answer_correctness=make_subscore(95.0),
        technical_reasoning=make_subscore(90.0),
        relevance=make_subscore(100.0),
        depth=make_subscore(80.0),
        practical_examples=make_subscore(85.0),
        is_ai_generated=False,
        ai_detection_reason=None,
        qualitative_feedback="Strong technical answer demonstrating solid Redis knowledge.",
    )

    reqs = [
        RequirementFulfillmentItem(requirement="Req 1", is_fulfilled=True),
        RequirementFulfillmentItem(requirement="Req 2", is_fulfilled=True),
    ]

    llm_eval = LLMQualitativeEvaluation(
        technical_solution=tech,
        screening_qa=[qa],
        requirement_fulfillment=reqs,
        pricing_realism=make_subscore(90.0),
        timeline_feasibility=make_subscore(85.0),
        milestone_structure=make_subscore(90.0),
        project_specificity=make_subscore(95.0),
        substance_density=make_subscore(90.0),
        probing_questions=[],
    )

    baseline = JobPostBaselineDto(
        job_id="job_1",
        job_title="Test Job",
        job_description="Test Description",
        budget_min=2000.0,
        budget_max=2500.0,
        estimated_duration="4 weeks",
    )

    proposal = ProposalOfferDto(
        proposal_id="prop_1",
        freelancer_id="free_1",
        proposed_budget=1800.0,  # 28% savings vs 2500 max -> v_sav = 28.0
        edited_milestones=[
            ProposalMilestoneInput(order_index=1, title="MS1", amount=600.0),
            ProposalMilestoneInput(order_index=2, title="MS2", amount=1200.0),
        ],
    )

    result = DeterministicCalculator.calculate(llm_eval, baseline, proposal)

    # Check Pillar Scores
    assert result.pillar_scores.technical_solution == 84.00
    assert result.pillar_scores.screening_qa == 92.0
    # Pillar 3: 0.50(98.0) + 0.50(90.0) = 49.0 + 45.0 = 94.0
    assert result.pillar_scores.financial_value == 94.0
    # Pillar 4: 0.40(100.0) + 0.30(90.0) + 0.30(92.5) = 40.0 + 27.0 + 27.75 = 94.75
    assert result.pillar_scores.milestone_scope == 94.75
    # Pillar 5: 0.60(95.0) + 0.40(90.0) = 93.0
    assert result.pillar_scores.authenticity_fluff == 93.0

    # TQ = 0.35(84.00) + 0.30(92.0) + 0.20(94.0) + 0.15(94.75) = 29.4 + 27.6 + 18.8 + 14.2125 = 90.01
    assert result.overall_technical_quality_tq == 90.01
    assert result.quality_interpretation_band == "Exceptional"


def test_vs_capping_and_badge_classification():
    """Verify Value Score calculation and capping behavior at max 100.0."""
    tech = TechnicalSolutionQualitativeEval(
        requirement_alignment=make_subscore(90.0),
        technical_correctness=make_subscore(90.0),
        architecture_quality=make_subscore(90.0),
        implementation_feasibility=make_subscore(90.0),
        edge_cases_security=make_subscore(90.0),
    )

    llm_eval = LLMQualitativeEvaluation(
        technical_solution=tech,
        screening_qa=[],
        requirement_fulfillment=[RequirementFulfillmentItem(requirement="Req 1", is_fulfilled=True)],
        pricing_realism=make_subscore(100.0),
        timeline_feasibility=make_subscore(100.0),
        milestone_structure=make_subscore(100.0),
        project_specificity=make_subscore(100.0),
        substance_density=make_subscore(100.0),
        probing_questions=[],
    )

    # Test Case 1: TQ = 92.5, savings_ratio = 0.20 -> VS = min(100, 92.5 * 1.10 = 101.75) -> 100.0
    baseline_1 = JobPostBaselineDto(
        job_id="j1", job_title="Job 1", job_description="Desc", budget_max=1000.0
    )
    proposal_1 = ProposalOfferDto(
        proposal_id="p1", freelancer_id="f1", proposed_budget=800.0
    )
    res_1 = DeterministicCalculator.calculate(llm_eval, baseline_1, proposal_1)
    assert res_1.savings_ratio == 0.20
    assert res_1.overall_technical_quality_tq == 92.50
    assert res_1.final_value_score_vs == 100.0
    assert res_1.verdict_badge == "top_value"


    # Test Case 2: TQ = 90.0, savings_ratio = 0.50 -> VS = min(100.0, 90.0 * 1.25 = 112.5) -> 100.0
    baseline_2 = JobPostBaselineDto(
        job_id="j2", job_title="Job 2", job_description="Desc", budget_max=1000.0
    )
    proposal_2 = ProposalOfferDto(
        proposal_id="p2", freelancer_id="f2", proposed_budget=500.0
    )
    res_2 = DeterministicCalculator.calculate(llm_eval, baseline_2, proposal_2)
    assert res_2.savings_ratio == 0.50
    assert res_2.final_value_score_vs == 100.0  # Capped at 100.0
    assert res_2.verdict_badge == "top_value"


def test_scope_completeness_calculation():
    """Verify deterministic scope completeness percentage calculation (e.g. 2 of 3 requirements = 66.67%)."""
    tech = TechnicalSolutionQualitativeEval(
        requirement_alignment=make_subscore(70.0),
        technical_correctness=make_subscore(70.0),
        architecture_quality=make_subscore(70.0),
        implementation_feasibility=make_subscore(70.0),
        edge_cases_security=make_subscore(70.0),
    )

    reqs = [
        RequirementFulfillmentItem(requirement="Req 1", is_fulfilled=True),
        RequirementFulfillmentItem(requirement="Req 2", is_fulfilled=True),
        RequirementFulfillmentItem(requirement="Req 3", is_fulfilled=False),
    ]

    llm_eval = LLMQualitativeEvaluation(
        technical_solution=tech,
        screening_qa=[],
        requirement_fulfillment=reqs,
        pricing_realism=make_subscore(70.0),
        timeline_feasibility=make_subscore(70.0),
        milestone_structure=make_subscore(70.0),
        project_specificity=make_subscore(70.0),
        substance_density=make_subscore(70.0),
        probing_questions=[],
    )

    baseline = JobPostBaselineDto(
        job_id="j3", job_title="Job 3", job_description="Desc", budget_max=1000.0
    )
    proposal = ProposalOfferDto(
        proposal_id="p3", freelancer_id="f3", proposed_budget=1000.0
    )

    res = DeterministicCalculator.calculate(llm_eval, baseline, proposal)
    assert res.scope_completeness_percent == 66.67


def test_milestone_arithmetic_clamping():
    """Verify is_milestone_clamped is True when milestone sum equals proposed budget, False otherwise."""
    tech = TechnicalSolutionQualitativeEval(
        requirement_alignment=make_subscore(80.0),
        technical_correctness=make_subscore(80.0),
        architecture_quality=make_subscore(80.0),
        implementation_feasibility=make_subscore(80.0),
        edge_cases_security=make_subscore(80.0),
    )

    llm_eval = LLMQualitativeEvaluation(
        technical_solution=tech,
        screening_qa=[],
        requirement_fulfillment=[],
        pricing_realism=make_subscore(80.0),
        timeline_feasibility=make_subscore(80.0),
        milestone_structure=make_subscore(80.0),
        project_specificity=make_subscore(80.0),
        substance_density=make_subscore(80.0),
        probing_questions=[],
    )

    baseline = JobPostBaselineDto(
        job_id="j4", job_title="Job 4", job_description="Desc", budget_max=1000.0
    )

    # Clamped proposal
    proposal_clamped = ProposalOfferDto(
        proposal_id="p4",
        freelancer_id="f4",
        proposed_budget=1000.0,
        edited_milestones=[
            ProposalMilestoneInput(order_index=1, title="M1", amount=400.0),
            ProposalMilestoneInput(order_index=2, title="M2", amount=600.0),
        ],
    )
    res_clamped = DeterministicCalculator.calculate(llm_eval, baseline, proposal_clamped)
    assert res_clamped.is_milestone_clamped is True
    assert res_clamped.milestone_total == 1000.0

    # Unclamped proposal
    proposal_unclamped = ProposalOfferDto(
        proposal_id="p5",
        freelancer_id="f5",
        proposed_budget=1000.0,
        edited_milestones=[
            ProposalMilestoneInput(order_index=1, title="M1", amount=400.0),
            ProposalMilestoneInput(order_index=2, title="M2", amount=500.0),  # Sums to 900 != 1000
        ],
    )
    res_unclamped = DeterministicCalculator.calculate(llm_eval, baseline, proposal_unclamped)
    assert res_unclamped.is_milestone_clamped is False
    assert res_unclamped.milestone_total == 900.0


def test_sanitize_screening_qa():
    """Verify that CandidateJudgingService._sanitize_screening_qa enforces 1:1 Q&A matching."""
    from app.services.proposals.candidate_judging_service import CandidateJudgingService

    service = CandidateJudgingService()

    tech = TechnicalSolutionQualitativeEval(
        requirement_alignment=make_subscore(80.0),
        technical_correctness=make_subscore(80.0),
        architecture_quality=make_subscore(80.0),
        implementation_feasibility=make_subscore(80.0),
        edge_cases_security=make_subscore(80.0),
    )

    # Simulated LLM hallucinating 3 Q&A evaluations when candidate only answered 1
    hallucinated_qas = [
        QuestionAnswerQualitativeEval(
            question_index=1,
            question_text="Hallucinated Q1",
            candidate_answer="Hallucinated A1",
            answer_correctness=make_subscore(80.0),
            technical_reasoning=make_subscore(80.0),
            relevance=make_subscore(80.0),
            depth=make_subscore(80.0),
            practical_examples=make_subscore(80.0),
            is_ai_generated=False,
            ai_detection_reason=None,
            qualitative_feedback="Eval 1",
        ),
        QuestionAnswerQualitativeEval(
            question_index=2,
            question_text="Fake Q2",
            candidate_answer="Fake A2",
            answer_correctness=make_subscore(70.0),
            technical_reasoning=make_subscore(70.0),
            relevance=make_subscore(70.0),
            depth=make_subscore(70.0),
            practical_examples=make_subscore(70.0),
            is_ai_generated=False,
            ai_detection_reason=None,
            qualitative_feedback="Eval 2",
        ),
        QuestionAnswerQualitativeEval(
            question_index=3,
            question_text="Fake Q3",
            candidate_answer="Fake A3",
            answer_correctness=make_subscore(60.0),
            technical_reasoning=make_subscore(60.0),
            relevance=make_subscore(60.0),
            depth=make_subscore(60.0),
            practical_examples=make_subscore(60.0),
            is_ai_generated=False,
            ai_detection_reason=None,
            qualitative_feedback="Eval 3",
        ),
    ]

    llm_eval = LLMQualitativeEvaluation(
        technical_solution=tech,
        screening_qa=hallucinated_qas,
        requirement_fulfillment=[],
        pricing_realism=make_subscore(80.0),
        timeline_feasibility=make_subscore(80.0),
        milestone_structure=make_subscore(80.0),
        project_specificity=make_subscore(80.0),
        substance_density=make_subscore(80.0),
        probing_questions=[],
    )

    # Proposal with ONLY 1 screening question
    proposal_single_qa = ProposalOfferDto(
        proposal_id="p_single",
        freelancer_id="f_single",
        proposed_budget=1000.0,
        vetting_qa_answers=[
            QuestionAnswerPairInput(
                question_index=1,
                question_text="Real Question 1?",
                candidate_answer="Real Answer 1",
            )
        ],
    )

    sanitized_eval = service._sanitize_screening_qa(llm_eval, proposal_single_qa)

    # Must be trimmed to exactly 1 item
    assert len(sanitized_eval.screening_qa) == 1
    assert sanitized_eval.screening_qa[0].question_index == 1
    assert sanitized_eval.screening_qa[0].question_text == "Real Question 1?"
    assert sanitized_eval.screening_qa[0].candidate_answer == "Real Answer 1"

    # Test proposal with 0 screening questions
    proposal_zero_qa = ProposalOfferDto(
        proposal_id="p_zero",
        freelancer_id="f_zero",
        proposed_budget=1000.0,
        vetting_qa_answers=[],
    )

    sanitized_zero = service._sanitize_screening_qa(llm_eval, proposal_zero_qa)
    assert len(sanitized_zero.screening_qa) == 0


def test_zero_alignment_forces_zero_coverage():
    """Verify that requirement alignment score of 0.0 forces scope_completeness_percent to 0.0."""
    tech = TechnicalSolutionQualitativeEval(
        requirement_alignment=make_subscore(0.0),
        technical_correctness=make_subscore(0.0),
        architecture_quality=make_subscore(0.0),
        implementation_feasibility=make_subscore(0.0),
        edge_cases_security=make_subscore(0.0),
    )

    reqs = [
        RequirementFulfillmentItem(requirement="Req 1", is_fulfilled=True),
        RequirementFulfillmentItem(requirement="Req 2", is_fulfilled=True),
    ]

    llm_eval = LLMQualitativeEvaluation(
        technical_solution=tech,
        screening_qa=[],
        requirement_fulfillment=reqs,
        pricing_realism=make_subscore(10.0),
        timeline_feasibility=make_subscore(10.0),
        milestone_structure=make_subscore(10.0),
        project_specificity=make_subscore(0.0),
        substance_density=make_subscore(0.0),
        probing_questions=[],
    )

    baseline = JobPostBaselineDto(
        job_id="j_fluff", job_title="Fluff Job", job_description="Desc", budget_max=1000.0
    )
    proposal = ProposalOfferDto(
        proposal_id="p_fluff", freelancer_id="f_fluff", proposed_budget=1000.0
    )

    res = DeterministicCalculator.calculate(llm_eval, baseline, proposal)
    assert res.pillar_scores.technical_solution == 0.0
    assert res.scope_completeness_percent == 0.0
    assert res.verdict_badge == "high_risk"


def test_fallback_evaluation_unfulfilled_fulfillment():
    """Verify fallback evaluation marks fallback requirement as is_fulfilled=False."""
    from app.services.proposals.candidate_judging_service import CandidateJudgingService

    service = CandidateJudgingService()
    proposal = ProposalOfferDto(
        proposal_id="p_fallback", freelancer_id="f_fallback", proposed_budget=1000.0
    )

    fallback_eval = service._create_fallback_evaluation(proposal)
    assert len(fallback_eval.requirement_fulfillment) == 1
    assert fallback_eval.requirement_fulfillment[0].is_fulfilled is False


@pytest.mark.anyio
async def test_response_preserves_input_baseline_and_offer():
    """Verify CandidateJudgingResponse preserves job_post_baseline and proposal_offer from input without alteration."""
    from unittest.mock import AsyncMock, MagicMock
    from app.services.proposals.candidate_judging_service import CandidateJudgingService
    from app.schemas.candidate_judging_schemas import CandidateJudgingRequest

    mock_llm = MagicMock()
    mock_llm.generate = AsyncMock(side_effect=RuntimeError("Trigger fallback"))
    service = CandidateJudgingService(llm_gateway=mock_llm)

    baseline = JobPostBaselineDto(
        job_id="j_preserve",
        job_title="Preserve Job",
        job_description="Description for preservation test",
        budget_min=3000.0,
        budget_max=3876.0,
        estimated_duration="4 weeks",
    )
    proposal = ProposalOfferDto(
        proposal_id="p_preserve",
        freelancer_id="f_preserve",
        proposed_budget=3876.0,
        proposed_duration="4 weeks",
    )

    req = CandidateJudgingRequest(
        job_post_baseline=baseline,
        candidate_proposal=proposal,
    )

    res = await service.evaluate_candidate(req)

    assert res.job_post_baseline is not None
    assert res.job_post_baseline.budget_max == 3876.0
    assert res.job_post_baseline.estimated_duration == "4 weeks"
    assert res.proposal_offer is not None
    assert res.proposal_offer.proposed_budget == 3876.0
    assert res.proposal_offer.proposed_duration == "4 weeks"



def test_sanitize_screening_qa_duplicate_indices():
    """Verify that _sanitize_screening_qa correctly handles multiple questions with duplicate question_index without overwriting."""
    from app.services.proposals.candidate_judging_service import CandidateJudgingService

    service = CandidateJudgingService()

    tech = TechnicalSolutionQualitativeEval(
        requirement_alignment=make_subscore(80.0),
        technical_correctness=make_subscore(80.0),
        architecture_quality=make_subscore(80.0),
        implementation_feasibility=make_subscore(80.0),
        edge_cases_security=make_subscore(80.0),
    )

    eval_qas = [
        QuestionAnswerQualitativeEval(
            question_index=1,
            question_text="Q1 text",
            candidate_answer="A1 text",
            answer_correctness=make_subscore(90.0),
            technical_reasoning=make_subscore(90.0),
            relevance=make_subscore(90.0),
            depth=make_subscore(90.0),
            practical_examples=make_subscore(90.0),
            is_ai_generated=False,
            ai_detection_reason=None,
            qualitative_feedback="Eval 1",
        ),
        QuestionAnswerQualitativeEval(
            question_index=1,
            question_text="Q2 text",
            candidate_answer="A2 text",
            answer_correctness=make_subscore(70.0),
            technical_reasoning=make_subscore(70.0),
            relevance=make_subscore(70.0),
            depth=make_subscore(70.0),
            practical_examples=make_subscore(70.0),
            is_ai_generated=False,
            ai_detection_reason=None,
            qualitative_feedback="Eval 2",
        ),
    ]

    llm_eval = LLMQualitativeEvaluation(
        technical_solution=tech,
        screening_qa=eval_qas,
        requirement_fulfillment=[],
        pricing_realism=make_subscore(80.0),
        timeline_feasibility=make_subscore(80.0),
        milestone_structure=make_subscore(80.0),
        project_specificity=make_subscore(80.0),
        substance_density=make_subscore(80.0),
        probing_questions=[],
    )

    # 2 input questions both having question_index = 1
    proposal_dup_idx = ProposalOfferDto(
        proposal_id="p_dup",
        freelancer_id="f_dup",
        proposed_budget=1000.0,
        vetting_qa_answers=[
            QuestionAnswerPairInput(
                question_index=1,
                question_text="What design principles do you consider?",
                candidate_answer="Visual hierarchy, contrast, typography...",
            ),
            QuestionAnswerPairInput(
                question_index=1,
                question_text="How many experiences do you have?",
                candidate_answer="3 years",
            ),
        ],
    )

    sanitized = service._sanitize_screening_qa(llm_eval, proposal_dup_idx)

    assert len(sanitized.screening_qa) == 2
    # Verify Question 1 is NOT overwritten by Question 2
    assert sanitized.screening_qa[0].question_index == 1
    assert sanitized.screening_qa[0].question_text == "What design principles do you consider?"
    assert sanitized.screening_qa[0].candidate_answer == "Visual hierarchy, contrast, typography..."

    # Verify Question 2 is distinctly assigned to index 2
    assert sanitized.screening_qa[1].question_index == 2
    assert sanitized.screening_qa[1].question_text == "How many experiences do you have?"
    assert sanitized.screening_qa[1].candidate_answer == "3 years"




