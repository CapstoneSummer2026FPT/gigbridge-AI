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
    # Pillar 1 subscores: 0.25(90) + 0.30(85) + 0.20(80) + 0.15(85) + 0.10(75) = 84.25
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
    assert result.pillar_scores.technical_solution == 84.25
    assert result.pillar_scores.screening_qa == 92.0
    # Pillar 3: 0.50(28.0) + 0.30(90.0) + 0.20(85.0) = 14.0 + 27.0 + 17.0 = 58.0
    assert result.pillar_scores.financial_value == 58.0
    # Pillar 4: 0.60(100.0) + 0.40(90.0) = 96.0
    assert result.pillar_scores.milestone_scope == 96.0
    # Pillar 5: 0.60(95.0) + 0.40(90.0) = 93.0
    assert result.pillar_scores.authenticity_fluff == 93.0

    # TQ = 0.35(84.25) + 0.30(92.0) + 0.20(58.0) + 0.15(96.0) = 29.4875 + 27.6 + 11.6 + 14.4 = 83.09
    assert result.overall_technical_quality_tq == 83.09
    assert result.quality_interpretation_band == "Strong"


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

    # Test Case 1: TQ = 85.5, savings_ratio = 0.20 -> VS = 85.5 * 1.10 = 94.05
    baseline_1 = JobPostBaselineDto(
        job_id="j1", job_title="Job 1", job_description="Desc", budget_max=1000.0
    )
    proposal_1 = ProposalOfferDto(
        proposal_id="p1", freelancer_id="f1", proposed_budget=800.0
    )
    res_1 = DeterministicCalculator.calculate(llm_eval, baseline_1, proposal_1)
    assert res_1.savings_ratio == 0.20
    assert res_1.overall_technical_quality_tq == 85.5
    assert res_1.final_value_score_vs == 94.05
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

