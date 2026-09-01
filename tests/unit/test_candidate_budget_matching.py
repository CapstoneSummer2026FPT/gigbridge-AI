import pytest
from app.schemas.matching import TalentRerankCandidate, TalentRerankJob
from app.services.matching.job_matching import JobMatchingService


def test_parse_duration_to_hours():
    service = JobMatchingService()
    assert service.parse_duration_to_hours("2 weeks") == 80.0
    assert service.parse_duration_to_hours("1 month") == 160.0
    assert service.parse_duration_to_hours("5 days") == 40.0
    assert service.parse_duration_to_hours("10 hours") == 10.0
    assert service.parse_duration_to_hours("invalid") is None
    assert service.parse_duration_to_hours(None) is None


def test_calculate_budget_bonus_milestone_and_hourly():
    service = JobMatchingService()

    # Case 1: Fixed milestone budget 2000 for 2 weeks (80 hrs) = 25/hr vs freelancer 20/hr (20% saving = +20 pts)
    job = TalentRerankJob(
        job_id="job1",
        title="Full Stack Developer",
        budget_amount=2000.0,
        budget_type="fixed",
        estimated_duration="2 weeks",
    )
    cand_saving_20 = TalentRerankCandidate(
        freelancer_id="f1",
        availability=1,
        expected_rate=20.0,
    )
    bonus, saving_pct = service._calculate_budget_bonus(job, cand_saving_20)
    assert saving_pct == 20.0
    assert bonus == 20.0

    # Case 2: 15% cost saving -> +15 pts
    cand_saving_15 = TalentRerankCandidate(
        freelancer_id="f2",
        availability=1,
        expected_rate=21.25, # (25 - 21.25)/25 = 0.15 (15%)
    )
    bonus, saving_pct = service._calculate_budget_bonus(job, cand_saving_15)
    assert saving_pct == 15.0
    assert bonus == 15.0

    # Case 3: 25% cost saving -> capped at +20 pts max
    cand_saving_25 = TalentRerankCandidate(
        freelancer_id="f3",
        availability=1,
        expected_rate=18.75, # (25 - 18.75)/25 = 0.25 (25%)
    )
    bonus, saving_pct = service._calculate_budget_bonus(job, cand_saving_25)
    assert saving_pct == 25.0
    assert bonus == 20.0 # Max cap

    # Case 4: Rate equals budget (0% saving) -> 0 bonus pts
    cand_exact = TalentRerankCandidate(
        freelancer_id="f4",
        availability=1,
        expected_rate=25.0,
    )
    bonus, saving_pct = service._calculate_budget_bonus(job, cand_exact)
    assert saving_pct == 0.0
    assert bonus == 0.0

    # Case 5: Rate over budget (negative saving) -> 0 bonus pts
    cand_over = TalentRerankCandidate(
        freelancer_id="f5",
        availability=1,
        expected_rate=30.0,
    )
    bonus, saving_pct = service._calculate_budget_bonus(job, cand_over)
    assert saving_pct == -20.0
    assert bonus == 0.0

    # Case 6: Missing expected rate -> 0 bonus pts and None saving_pct
    cand_no_rate = TalentRerankCandidate(
        freelancer_id="f6",
        availability=1,
    )
    bonus, saving_pct = service._calculate_budget_bonus(job, cand_no_rate)
    assert saving_pct is None
    assert bonus == 0.0
