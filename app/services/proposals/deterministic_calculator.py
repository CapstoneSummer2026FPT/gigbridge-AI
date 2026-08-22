"""
PURPOSE: Deterministic Python Mathematical Calculator for Candidate Evaluation Engine.
IMPORTANCE: Critical — Ensures LLM never invents arbitrary top-level scores. All weighted sums, budget ratios, scope completeness percentages, score capping, interpretation bands, and verdict badges are calculated deterministically in Python.
"""

from typing import List
from app.schemas.candidate_judging_schemas import (
    LLMQualitativeEvaluation,
    JobPostBaselineDto,
    ProposalOfferDto,
    DeterministicCalculations,
    PillarScores,
)


class DeterministicCalculator:
    """Executes verifiable mathematical aggregation on LLM qualitative feature outputs."""

    @staticmethod
    def calculate(
        llm_eval: LLMQualitativeEvaluation,
        baseline: JobPostBaselineDto,
        proposal: ProposalOfferDto,
    ) -> DeterministicCalculations:
        # 1. Milestone Arithmetic Validation
        milestone_total = sum(m.amount for m in proposal.edited_milestones) if proposal.edited_milestones else proposal.proposed_budget
        proposed_budget = proposal.proposed_budget
        is_milestone_clamped = abs(milestone_total - proposed_budget) < 0.01

        # 2. Budget Savings Ratio Calculation
        budget_max = baseline.budget_max or 0.0
        if budget_max > 0.0 and proposed_budget <= budget_max:
            savings_ratio = max(0.0, (budget_max - proposed_budget) / budget_max)
        else:
            savings_ratio = 0.0
        savings_ratio_percent = round(savings_ratio * 100.0, 2)
        v_sav = min(100.0, savings_ratio_percent)

        # 3. Deterministic Scope Completeness Calculation
        requirements = llm_eval.requirement_fulfillment
        if requirements and len(requirements) > 0:
            fulfilled_count = sum(1 for req in requirements if req.is_fulfilled)
            scope_completeness_percent = round((fulfilled_count / len(requirements)) * 100.0, 2)
        else:
            scope_completeness_percent = 100.0

        # 4. Pillar 1: Technical Solution Score (35% weight)
        tech = llm_eval.technical_solution
        p1 = (
            0.25 * tech.requirement_alignment.score
            + 0.30 * tech.technical_correctness.score
            + 0.20 * tech.architecture_quality.score
            + 0.15 * tech.implementation_feasibility.score
            + 0.10 * tech.edge_cases_security.score
        )
        p1 = round(p1, 2)

        # 5. Pillar 2: Vetting Screening Q&A Score (30% weight)
        qa_list = llm_eval.screening_qa
        if qa_list and len(qa_list) > 0:
            qa_scores = []
            for qa in qa_list:
                q_score = (
                    0.40 * qa.answer_correctness.score
                    + 0.25 * qa.technical_reasoning.score
                    + 0.15 * qa.relevance.score
                    + 0.10 * qa.depth.score
                    + 0.10 * qa.practical_examples.score
                )
                qa_scores.append(q_score)
            p2 = round(sum(qa_scores) / len(qa_scores), 2)
        else:
            # Default to technical solution score if no screening questions present
            p2 = p1

        # 6. Pillar 3: Financial & Timeline Value Score (20% weight)
        v_price = llm_eval.pricing_realism.score
        v_time = llm_eval.timeline_feasibility.score
        p3 = round(0.50 * v_sav + 0.30 * v_price + 0.20 * v_time, 2)

        # 7. Pillar 4: Milestone Scope & Deliverables Score (10% weight)
        m_struct = llm_eval.milestone_structure.score
        p4 = round(0.60 * scope_completeness_percent + 0.40 * m_struct, 2)

        # 8. Pillar 5: Authenticity & Fluff Control Score (5% weight)
        a_spec = llm_eval.project_specificity.score
        a_conc = llm_eval.substance_density.score
        p5 = round(0.60 * a_spec + 0.40 * a_conc, 2)

        # 9. Overall Technical Quality (TQ) Score (0.0 to 100.0)
        tq = round(0.35 * p1 + 0.30 * p2 + 0.20 * p3 + 0.10 * p4 + 0.05 * p5, 2)

        # 10. Capped Value Score (VS) (0.0 to 100.0)
        raw_vs = tq * (1.0 + savings_ratio * 0.5)
        vs = round(min(100.0, max(0.0, raw_vs)), 2)

        # 11. Post-Calculation Interpretation Band
        if tq >= 90.0:
            interpretation_band = "Exceptional"
        elif tq >= 75.0:
            interpretation_band = "Strong"
        elif tq >= 60.0:
            interpretation_band = "Acceptable"
        else:
            interpretation_band = "High Risk / Poor Quality"

        # 12. Verdict Badge Classification
        if tq < 60.0 or scope_completeness_percent < 70.0:
            badge = "high_risk"
        elif tq >= 80.0 and vs >= 88.0 and (budget_max == 0.0 or proposed_budget <= budget_max):
            badge = "top_value"
        elif tq >= 90.0 and budget_max > 0.0 and proposed_budget > budget_max:
            badge = "top_technical"
        elif 60.0 <= tq < 80.0 and savings_ratio >= 0.20:
            badge = "budget_saver"
        elif vs >= 85.0:
            badge = "top_value"
        elif savings_ratio >= 0.15:
            badge = "budget_saver"
        else:
            badge = "high_risk" if tq < 65.0 else "top_technical"

        pillar_scores = PillarScores(
            technical_solution=p1,
            screening_qa=p2,
            financial_value=p3,
            milestone_scope=p4,
            authenticity_fluff=p5,
        )

        return DeterministicCalculations(
            milestone_total=milestone_total,
            proposed_budget=proposed_budget,
            is_milestone_clamped=is_milestone_clamped,
            savings_ratio=savings_ratio,
            savings_ratio_percent=savings_ratio_percent,
            scope_completeness_percent=scope_completeness_percent,
            pillar_scores=pillar_scores,
            overall_technical_quality_tq=tq,
            quality_interpretation_band=interpretation_band,
            final_value_score_vs=vs,
            verdict_badge=badge,
        )
