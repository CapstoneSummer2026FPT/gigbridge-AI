import sys
import os

# Ensure app package is importable
sys.path.insert(0, os.path.abspath("."))

from app.schemas.candidate_judging_schemas import (
    JobPostBaselineDto,
    ProposalOfferDto,
    JobPostMilestoneInput,
    ProposalMilestoneInput,
    LLMQualitativeEvaluation,
    TechnicalSolutionQualitativeEval,
    SubcriteriaScoreWithEvidence,
    RequirementFulfillmentItem,
    MilestoneAuditItem,
)
from app.services.proposals.deterministic_calculator import DeterministicCalculator

print("--- Testing Milestone Delta Classification & Deterministic Score Calculation ---")

baseline = JobPostBaselineDto(
    job_id="job_123",
    job_title="FastAPI & ChromaDB Ingestion Service",
    job_description="Develop FastAPI app handling cold starts, implement ingestion process checking chroma_db folder and flagging needs_ingestion, rebuild database dynamically.",
    budget_min=1000.0,
    budget_max=1000.0,
    estimated_duration="4 weeks",
    original_milestones=[
        JobPostMilestoneInput(order_index=1, title="Initial Setup", amount=250.0, estimated_duration="1 week"),
        JobPostMilestoneInput(order_index=2, title="Implement Ingestion", amount=250.0, estimated_duration="1 week"),
        JobPostMilestoneInput(order_index=3, title="Testing & Optimization", amount=250.0, estimated_duration="1 week"),
        JobPostMilestoneInput(order_index=4, title="Documentation & Deployment", amount=250.0, estimated_duration="1 week"),
    ]
)

proposal = ProposalOfferDto(
    proposal_id="prop_456",
    freelancer_id="free_789",
    proposed_budget=1000.0,
    proposed_duration="4 weeks",
    solution_approach="I will build the FastAPI service with async ChromaDB ingestion worker...",
    edited_milestones=[
        ProposalMilestoneInput(order_index=1, title="Initial Setup and Configuration", amount=250.0, estimated_duration="1 week"),
        ProposalMilestoneInput(order_index=2, title="Implement Ingestion Process & ChromaDB Flagging", amount=250.0, estimated_duration="1 week"),
        ProposalMilestoneInput(order_index=3, title="Testing and Optimization", amount=250.0, estimated_duration="1 week"),
        ProposalMilestoneInput(order_index=4, title="Final Review and Documentation", amount=250.0, estimated_duration="1 week"),
    ]
)

sub_score = SubcriteriaScoreWithEvidence(score=85.0, evidence=[])

eval_output = LLMQualitativeEvaluation(
    technical_solution=TechnicalSolutionQualitativeEval(
        requirement_alignment=sub_score,
        technical_correctness=sub_score,
        architecture_quality=sub_score,
        implementation_feasibility=sub_score,
        edge_cases_security=sub_score,
    ),
    milestone_audit=[
        MilestoneAuditItem(order_index=1, milestone_title="Initial Setup and Configuration", status="Preserved", change_summary="Unchanged", is_scope_covered=True),
        MilestoneAuditItem(order_index=2, milestone_title="Implement Ingestion Process & ChromaDB Flagging", status="Edited", change_summary="Freelancer specified chroma_db & needs_ingestion logic", is_scope_covered=True),
        MilestoneAuditItem(order_index=3, milestone_title="Testing and Optimization", status="Preserved", change_summary="Unchanged", is_scope_covered=True),
        MilestoneAuditItem(order_index=4, milestone_title="Final Review and Documentation", status="Preserved", change_summary="Unchanged", is_scope_covered=True),
    ],
    requirement_fulfillment=[
        RequirementFulfillmentItem(
            requirement="Develop and implement marketing automation strategies to drive traffic",
            is_fulfilled=True,
            matched_milestone="Milestone 1: Marketing Automation Setup",
            evidence_quote="We will configure automated lead nurture workflows in HubSpot and set up email triggers to drive traffic.",
            note="Directly covered in Milestone 1 deliverables."
        ),
        RequirementFulfillmentItem(
            requirement="Optimize SEO and content marketing efforts",
            is_fulfilled=True,
            matched_milestone="Milestone 2: SEO Optimization",
            evidence_quote="Perform technical SEO audits, keyword research, and optimize content structure.",
            note="Covered in Milestone 2."
        ),
        RequirementFulfillmentItem(
            requirement="Collaborate with the content team to create compelling marketing materials",
            is_fulfilled=False,
            matched_milestone=None,
            evidence_quote="No content creation, copywriting, or team collaboration workflow mentioned in proposal or milestones.",
            note="Candidate proposal focuses strictly on technical automation setup, omitting content creation."
        ),
    ],
    pricing_realism=sub_score,
    timeline_feasibility=sub_score,
    milestone_structure=sub_score,
    project_specificity=sub_score,
    substance_density=sub_score,
)

res = DeterministicCalculator.calculate(eval_output, baseline, proposal)

print(f"Scope Completeness %: {res.scope_completeness_percent}%")
print(f"Pillar 4 Score (Milestone Scope): {res.pillar_scores.milestone_scope}")
print(f"Overall Technical Quality (TQ): {res.overall_technical_quality_tq}")
print(f"Verdict Badge: {res.verdict_badge}")
print("--- TEST PASSED SUCCESSFULLY ---")
