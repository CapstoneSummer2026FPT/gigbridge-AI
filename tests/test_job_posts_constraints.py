"""
Unit tests for the deterministic post-generation constraint helpers in
app.services.job_posts.  These helpers ensure that AI-generated milestone
plans always respect the approved budget and duration from the JD,
regardless of what the LLM produced.
"""

from datetime import date, timedelta
from math import ceil
from types import SimpleNamespace

import pytest

from app.services.job_posts import (
    _clamp_milestone_budgets,
    _clamp_milestone_durations,
    _recalculate_due_dates,
    _strip_budget_and_timeline_sections,
    format_weeks_to_duration,
    parse_duration_to_weeks,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_milestones(*specs):
    """Create a list of simple namespace objects that mimic MilestoneGenerationResponse.

    Each *spec* is a tuple: (amount, estimated_duration).
    due_date is initialised to a placeholder; tests that care about it pass
    through _recalculate_due_dates beforehand.
    """
    return [
        SimpleNamespace(amount=amt, estimated_duration=dur, due_date="2099-01-01")
        for amt, dur in specs
    ]


# ---------------------------------------------------------------------------
# parse_duration_to_weeks
# ---------------------------------------------------------------------------

class TestParseDurationToWeeks:
    def test_weeks_singular(self):
        assert parse_duration_to_weeks("1 week") == pytest.approx(1.0)

    def test_weeks_plural(self):
        assert parse_duration_to_weeks("4 weeks") == pytest.approx(4.0)

    def test_months(self):
        # 1 month ≈ 4.333 weeks
        assert parse_duration_to_weeks("1 month") == pytest.approx(4.333, rel=1e-3)

    def test_months_plural(self):
        assert parse_duration_to_weeks("3 months") == pytest.approx(12.999, rel=1e-3)

    def test_years(self):
        assert parse_duration_to_weeks("1 year") == pytest.approx(52.0)

    def test_vietnamese_tuan(self):
        assert parse_duration_to_weeks("2 tuần") == pytest.approx(2.0)

    def test_vietnamese_thang(self):
        assert parse_duration_to_weeks("1 tháng") == pytest.approx(4.333, rel=1e-3)

    def test_empty_string(self):
        assert parse_duration_to_weeks("") == 0.0

    def test_unparseable_string(self):
        assert parse_duration_to_weeks("a few weeks") == 0.0

    def test_single_word_no_unit(self):
        assert parse_duration_to_weeks("2") == 0.0

    def test_unknown_unit(self):
        assert parse_duration_to_weeks("2 fortnights") == 0.0


# ---------------------------------------------------------------------------
# format_weeks_to_duration
# ---------------------------------------------------------------------------

class TestFormatWeeksToDuration:
    def test_singular_one_week(self):
        assert format_weeks_to_duration(1.0) == "1 week"

    def test_plural_two_weeks(self):
        assert format_weeks_to_duration(2.0) == "2 weeks"

    def test_rounds_to_nearest(self):
        assert format_weeks_to_duration(2.4) == "2 weeks"
        assert format_weeks_to_duration(2.6) == "3 weeks"

    def test_minimum_one_week(self):
        assert format_weeks_to_duration(0.0) == "1 week"
        assert format_weeks_to_duration(0.3) == "1 week"


# ---------------------------------------------------------------------------
# _clamp_milestone_budgets
# ---------------------------------------------------------------------------

class TestClampMilestoneBudgets:
    def test_no_op_when_budget_zero(self):
        ms = make_milestones((100, "1 week"), (200, "1 week"))
        _clamp_milestone_budgets(ms, 0)
        assert ms[0].amount == 100
        assert ms[1].amount == 200

    def test_no_op_when_already_correct(self):
        ms = make_milestones((300, "1 week"), (200, "1 week"))
        _clamp_milestone_budgets(ms, 500)
        assert ms[0].amount == pytest.approx(300, abs=0.01)
        assert ms[1].amount == pytest.approx(200, abs=0.01)

    def test_scales_up_when_total_is_low(self):
        # Total = 300, approved = 500  →  each scaled by 5/3
        ms = make_milestones((100, "1 week"), (200, "1 week"))
        _clamp_milestone_budgets(ms, 500)
        total = sum(m.amount for m in ms)
        assert total == pytest.approx(500, abs=0.02)

    def test_scales_down_when_total_is_high(self):
        # Total = 900, approved = 500
        ms = make_milestones((600, "1 week"), (300, "1 week"))
        _clamp_milestone_budgets(ms, 500)
        total = sum(m.amount for m in ms)
        assert total == pytest.approx(500, abs=0.02)

    def test_three_milestones_sum_exact(self):
        ms = make_milestones((100, "1 week"), (150, "1 week"), (50, "1 week"))
        _clamp_milestone_budgets(ms, 400)
        total = sum(m.amount for m in ms)
        assert total == pytest.approx(400, abs=0.02)

    def test_all_zero_amounts_distributes_evenly(self):
        ms = make_milestones((0, "1 week"), (0, "1 week"))
        _clamp_milestone_budgets(ms, 200)
        total = sum(m.amount for m in ms)
        assert total == pytest.approx(200, abs=0.02)

    def test_preserves_proportional_distribution(self):
        # 25% / 75% split should be maintained after scaling
        ms = make_milestones((250, "1 week"), (750, "1 week"))
        _clamp_milestone_budgets(ms, 400)
        assert ms[0].amount == pytest.approx(100, abs=0.1)
        assert ms[1].amount == pytest.approx(300, abs=0.1)


# ---------------------------------------------------------------------------
# _clamp_milestone_durations
# ---------------------------------------------------------------------------

class TestClampMilestoneDurations:
    def test_no_op_when_approved_weeks_zero(self):
        ms = make_milestones((100, "3 weeks"), (100, "3 weeks"))
        _clamp_milestone_durations(ms, 0)
        assert ms[0].estimated_duration == "3 weeks"
        assert ms[1].estimated_duration == "3 weeks"

    def test_no_op_when_within_limit(self):
        ms = make_milestones((100, "2 weeks"), (100, "2 weeks"))
        _clamp_milestone_durations(ms, 5)
        assert ms[0].estimated_duration == "2 weeks"
        assert ms[1].estimated_duration == "2 weeks"

    def test_reduces_when_over_limit(self):
        # 3+3 = 6 weeks, limit = 4 weeks
        ms = make_milestones((100, "3 weeks"), (100, "3 weeks"))
        _clamp_milestone_durations(ms, 4)
        total = sum(parse_duration_to_weeks(m.estimated_duration) for m in ms)
        assert total <= 4.0 + 0.5  # allow rounding of ≤ 0.5 weeks

    def test_total_does_not_exceed_limit(self):
        ms = make_milestones((100, "2 weeks"), (100, "2 weeks"), (100, "2 weeks"))
        _clamp_milestone_durations(ms, 4)
        total = sum(parse_duration_to_weeks(m.estimated_duration) for m in ms)
        assert total <= 4.0 + 0.5

    def test_each_milestone_minimum_one_week(self):
        # Even extreme scale-down should leave each milestone at ≥ 1 week
        ms = make_milestones((100, "10 weeks"), (100, "10 weeks"))
        _clamp_milestone_durations(ms, 2)
        for m in ms:
            assert parse_duration_to_weeks(m.estimated_duration) >= 1.0

    def test_no_op_exact_match(self):
        ms = make_milestones((100, "2 weeks"), (100, "2 weeks"))
        _clamp_milestone_durations(ms, 4)
        assert ms[0].estimated_duration == "2 weeks"
        assert ms[1].estimated_duration == "2 weeks"


# ---------------------------------------------------------------------------
# _recalculate_due_dates
# ---------------------------------------------------------------------------

class TestRecalculateDueDates:
    def test_sequential_from_start(self):
        start = date(2025, 1, 1)
        ms = make_milestones((100, "2 weeks"), (100, "2 weeks"))
        _recalculate_due_dates(ms, start)

        expected_first = start + timedelta(days=ceil(2 * 7))
        expected_second = expected_first + timedelta(days=ceil(2 * 7))

        assert ms[0].due_date == expected_first.strftime("%Y-%m-%d")
        assert ms[1].due_date == expected_second.strftime("%Y-%m-%d")

    def test_dates_are_strictly_increasing(self):
        start = date(2025, 3, 1)
        ms = make_milestones((100, "1 week"), (100, "3 weeks"), (100, "2 weeks"))
        _recalculate_due_dates(ms, start)
        dates = [m.due_date for m in ms]
        assert dates == sorted(dates)  # ISO strings sort correctly

    def test_last_due_date_respects_total_duration(self):
        start = date(2025, 1, 1)
        approved_weeks = 4
        ms = make_milestones((100, "2 weeks"), (100, "2 weeks"))
        _clamp_milestone_durations(ms, approved_weeks)
        _recalculate_due_dates(ms, start)

        latest_allowed = start + timedelta(days=ceil(approved_weeks * 7))
        last_due = date.fromisoformat(ms[-1].due_date)
        assert last_due <= latest_allowed

    def test_format_is_iso(self):
        start = date(2025, 6, 15)
        ms = make_milestones((100, "1 week"),)
        _recalculate_due_dates(ms, start)
        # Should parse without error
        result = date.fromisoformat(ms[0].due_date)
        assert result > start


# ---------------------------------------------------------------------------
# _strip_budget_and_timeline_sections
# ---------------------------------------------------------------------------

class TestStripBudgetAndTimelineSections:
    def test_strips_budget_section(self):
        raw_text = (
            "ABOUT THE ROLE\n"
            "We are seeking an ASP.NET developer.\n\n"
            "KEY RESPONSIBILITIES\n"
            "- Build OTP email verification.\n\n"
            "BUDGET\n"
            "- Estimated budget: 10,000 GC.\n"
            "- Estimated duration: 1 month."
        )
        cleaned = _strip_budget_and_timeline_sections(raw_text)
        assert "BUDGET" not in cleaned
        assert "10,000 GC" not in cleaned
        assert "1 month" not in cleaned
        assert "ABOUT THE ROLE" in cleaned
        assert "KEY RESPONSIBILITIES" in cleaned

    def test_strips_salary_bullet_line_under_what_we_offer(self):
        raw_text = (
            "WHAT WE OFFER\n"
            "- Competitive salary in GigCoins.\n"
            "- Flexible working environment."
        )
        cleaned = _strip_budget_and_timeline_sections(raw_text)
        assert "Competitive salary in GigCoins" not in cleaned
        assert "Flexible working environment" in cleaned

    def test_vietnamese_budget_section(self):
        raw_text = (
            "YÊU CẦU CÔNG VIỆC\n"
            "- Có kinh nghiệm React.\n\n"
            "NGÂN SÁCH\n"
            "- Ngân sách dự kiến: 15.000.000 VNĐ.\n"
            "- Thời gian dự kiến: 2 tuần."
        )
        cleaned = _strip_budget_and_timeline_sections(raw_text)
        assert "NGÂN SÁCH" not in cleaned
        assert "15.000.000 VNĐ" not in cleaned
        assert "YÊU CẦU CÔNG VIỆC" in cleaned

