import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.schemas.candidate_judging_schemas import (
    JobPostBaselineDto,
    ProposalOfferDto,
    JobPostMilestoneInput,
    ProposalMilestoneInput,
    LLMQualitativeEvaluation,
    TechnicalSolutionQualitativeEval,
    SubcriteriaScoreWithEvidence,
)
from app.services.proposals.candidate_judging_service import CandidateJudgingService

def test_milestone_audit_sanitization():
    service = CandidateJudgingService()

    # 1. Client Baseline has 4 milestones
    baseline = JobPostBaselineDto(
        job_id="job-123",
        job_title="Full Stack OTP App",
        job_description="Build OTP verification system",
        original_milestones=[
            JobPostMilestoneInput(order_index=1, title="Design OTP System", amount=500.0, estimated_duration="2 weeks"),
            JobPostMilestoneInput(order_index=2, title="Implement OTP Verification", amount=500.0, estimated_duration="2 weeks"),
            JobPostMilestoneInput(order_index=3, title="Integrate OTP with Registration", amount=500.0, estimated_duration="2 weeks"),
            JobPostMilestoneInput(order_index=4, title="Email Provider Setup", amount=500.0, estimated_duration="1 week"),
        ]
    )

    # 2. Freelancer proposal:
    # - Milestone 1: Preserved
    # - Milestone 2: Edited (amount changed from 500 to 600)
    # - Milestone 4: Deleted (omitted)
    # - Milestone 5: Added (new custom phase)
    proposal = ProposalOfferDto(
        proposal_id="prop-456",
        freelancer_id="free-1",
        proposed_budget=1700.0,
        proposed_duration="6 weeks",
        edited_milestones=[
            ProposalMilestoneInput(order_index=1, title="Design OTP System", amount=500.0, estimated_duration="2 weeks"),
            ProposalMilestoneInput(order_index=2, title="Implement OTP Verification", amount=600.0, estimated_duration="2 weeks"),
            ProposalMilestoneInput(order_index=3, title="Integrate OTP with Registration", amount=500.0, estimated_duration="2 weeks"),
            ProposalMilestoneInput(order_index=5, title="Post-launch Bug Fixes", amount=100.0, estimated_duration="1 week"),
        ]
    )

    dummy_sub = SubcriteriaScoreWithEvidence(score=80.0, evidence=[])
    llm_eval = LLMQualitativeEvaluation(
        technical_solution=TechnicalSolutionQualitativeEval(
            requirement_alignment=dummy_sub,
            technical_correctness=dummy_sub,
            architecture_quality=dummy_sub,
            implementation_feasibility=dummy_sub,
            edge_cases_security=dummy_sub,
        ),
        pricing_realism=dummy_sub,
        timeline_feasibility=dummy_sub,
        milestone_structure=dummy_sub,
        project_specificity=dummy_sub,
        substance_density=dummy_sub,
        milestone_audit=[]  # Empty from LLM
    )

    sanitized = service._sanitize_milestone_audit(llm_eval, baseline, proposal)
    print("\n--- SANITIZED MILESTONE AUDIT RESULTS ---")
    for item in sanitized.milestone_audit:
        print(f"Title: {item.milestone_title} | Status: {item.status} | Covered: {item.is_scope_covered} | Summary: {item.change_summary}")

    statuses = [item.status for item in sanitized.milestone_audit]
    assert "Preserved" in statuses, "Should contain Preserved status"
    assert "Edited" in statuses, "Should contain Edited status"
    assert "Added" in statuses, "Should contain Added status"
    assert "Deleted" in statuses, "Should contain Deleted status"
    print("\nSUCCESS! All 4 milestone statuses verified accurately.")

if __name__ == "__main__":
    test_milestone_audit_sanitization()
