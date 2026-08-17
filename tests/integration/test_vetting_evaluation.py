import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.interviews import (
    AnalyzeVettingRequest,
    QuestionAnswerPair,
    InterviewFeedback,
    GradedQuestion,
)
from app.services.interviews import InterviewService


def test_weighted_average_calculation():
    # Test programmatic math calculation logic:
    # Easy (1.0), Medium (1.5), Hard (2.0)
    # GradedQuestions:
    # 1. Easy: score 80
    # 2. Medium: score 90
    # 3. Hard: score 70
    # Expected weighted score: (80*1.0 + 90*1.5 + 70*2.0) / (1.0 + 1.5 + 2.0) = 355 / 4.5 = 78.89 -> round to 79
    # Add holistic adjustment of 5 -> 79 + 5 = 84

    service = InterviewService(llm_gateway=MagicMock(), voice_service=MagicMock())
    
    mock_feedback = InterviewFeedback(
        score=0,
        summary="Test summary",
        technical_skills=["Python"],
        soft_skills=["Communication"],
        recommended_hire=True,
        holistic_adjustment=5,
        holistic_adjustment_reason="Good explanations",
        graded_questions=[
            GradedQuestion(
                question_index=1,
                question_text="Q1",
                question_type="theoretical",
                difficulty="easy",
                candidate_answer="A1",
                score=80,
                feedback="Good",
            ),
            GradedQuestion(
                question_index=2,
                question_text="Q2",
                question_type="problem_solving",
                difficulty="medium",
                candidate_answer="A2",
                score=90,
                feedback="Very Good",
            ),
            GradedQuestion(
                question_index=3,
                question_text="Q3",
                question_type="problem_solving",
                difficulty="hard",
                candidate_answer="A3",
                score=70,
                feedback="Decent",
            ),
        ]
    )

    # We mock self.llm.generate to return the serialized JSON representation of mock_feedback
    service.llm.generate = AsyncMock(return_value=mock_feedback.model_dump_json())

    request = AnalyzeVettingRequest(
        freelancer_id="free-1",
        job_title="Dev",
        job_description="Desc",
        job_skills=["Python"],
        qa_pairs=[
            QuestionAnswerPair(question_index=1, question_text="Q1", candidate_answer="A1"),
            QuestionAnswerPair(question_index=2, question_text="Q2", candidate_answer="A2"),
            QuestionAnswerPair(question_index=3, question_text="Q3", candidate_answer="A3"),
        ]
    )

    result = asyncio.run(service.analyze_vetting(request))
    assert result.score == 84


def test_holistic_adjustment_boundaries():
    # Test boundary clipping for final score:
    # 1. Base Score = 95, holistic_adjustment = 10 -> Expected final score: 100 (clipped)
    # 2. Base Score = 10, holistic_adjustment = -15 -> Expected final score: 0 (clipped)
    service = InterviewService(llm_gateway=MagicMock(), voice_service=MagicMock())

    # Case 1: clip high to 100
    mock_feedback_high = InterviewFeedback(
        score=0, summary="x", technical_skills=[], soft_skills=[], recommended_hire=True,
        holistic_adjustment=10, holistic_adjustment_reason="x",
        graded_questions=[
            GradedQuestion(
                question_index=1, question_text="Q1", question_type="theoretical", difficulty="easy",
                candidate_answer="A1", score=95, feedback="x"
            )
        ]
    )
    service.llm.generate = AsyncMock(return_value=mock_feedback_high.model_dump_json())

    request = AnalyzeVettingRequest(
        freelancer_id="free-1", job_title="Dev", qa_pairs=[
            QuestionAnswerPair(question_index=1, question_text="Q1", candidate_answer="A1")
        ]
    )
    result_high = asyncio.run(service.analyze_vetting(request))
    assert result_high.score == 100

    # Case 2: clip low to 0
    mock_feedback_low = InterviewFeedback(
        score=0, summary="x", technical_skills=[], soft_skills=[], recommended_hire=False,
        holistic_adjustment=-15, holistic_adjustment_reason="x",
        graded_questions=[
            GradedQuestion(
                question_index=1, question_text="Q1", question_type="theoretical", difficulty="easy",
                candidate_answer="A1", score=10, feedback="x"
            )
        ]
    )
    service.llm.generate = AsyncMock(return_value=mock_feedback_low.model_dump_json())
    result_low = asyncio.run(service.analyze_vetting(request))
    assert result_low.score == 0


def test_empty_or_zero_weight_fallback():
    # Verify that if no questions are returned by LLM, score defaults to 0 safely without division-by-zero
    service = InterviewService(llm_gateway=MagicMock(), voice_service=MagicMock())
    mock_feedback = InterviewFeedback(
        score=0, summary="x", technical_skills=[], soft_skills=[], recommended_hire=False,
        holistic_adjustment=0, holistic_adjustment_reason="x",
        graded_questions=[]
    )
    service.llm.generate = AsyncMock(return_value=mock_feedback.model_dump_json())
    request = AnalyzeVettingRequest(
        freelancer_id="free-1", job_title="Dev", qa_pairs=[]
    )
    result = asyncio.run(service.analyze_vetting(request))
    assert result.score == 0


def test_endpoint_success_schema_mapping():
    # Use fastapi TestClient to hit /api/ai/interviews/analyze-vetting
    client = TestClient(app)
    
    mock_feedback = InterviewFeedback(
        score=85,
        summary="Holistic view",
        technical_skills=["FastAPI"],
        soft_skills=["Writing"],
        recommended_hire=True,
        holistic_adjustment=-5,
        holistic_adjustment_reason="Tired candidate",
        graded_questions=[
            GradedQuestion(
                question_index=1,
                question_text="Tell me about FastAPI",
                question_type="theoretical",
                difficulty="medium",
                candidate_answer="It is fast",
                score=90,
                feedback="Correct",
            )
        ]
    )

    payload = {
        "freelancer_id": "freelancer-abc",
        "job_title": "Python Engineer",
        "job_description": "We need a Python developer",
        "job_skills": ["Python", "FastAPI"],
        "qa_pairs": [
            {
                "question_index": 1,
                "question_text": "Tell me about FastAPI",
                "candidate_answer": "It is fast"
            }
        ]
    }

    from app.services.interviews import get_interview_service
    mock_service = MagicMock()
    mock_service.analyze_vetting = AsyncMock(return_value=mock_feedback)
    app.dependency_overrides[get_interview_service] = lambda: mock_service

    try:
        response = client.post(
            "/api/ai/interviews/ai-interview-judging",
            json=payload,
            headers={"X-API-Key": "dev-key-please-change-in-env"}  # Bypass API key check for tests
        )

        assert response.status_code == 200
        json_data = response.json()
        assert json_data["success"] is True
        assert json_data["data"]["score"] == 85
        assert json_data["data"]["summary"] == "Holistic view"
        assert json_data["data"]["graded_questions"][0]["question_type"] == "theoretical"
        assert json_data["data"]["graded_questions"][0]["score"] == 90
    finally:
        app.dependency_overrides.clear()


def test_invalid_payload_triggers_validation_error():
    client = TestClient(app)
    
    # Missing freelancer_id and qa_pairs
    payload = {
        "job_title": "Python Engineer"
    }

    response = client.post(
        "/api/ai/interviews/ai-interview-judging",
        json=payload,
        headers={"X-API-Key": "dev-key-please-change-in-env"}
    )
    
    assert response.status_code == 422
    assert "errors" in response.json()


def test_experience_question_exclusion():
    # Test that experience questions are ignored in weighted average math:
    # 1. Easy Theoretical: score 80 (weight 1.0)
    # 2. Medium Problem Solving: score 90 (weight 1.5)
    # 3. Medium Experience: score 30 (weight 1.5) -> should be excluded!
    # Expected weighted score: (80*1.0 + 90*1.5) / (1.0 + 1.5) = 215 / 2.5 = 86
    service = InterviewService(llm_gateway=MagicMock(), voice_service=MagicMock())
    
    mock_feedback = InterviewFeedback(
        score=0,
        summary="Test summary",
        technical_skills=["Python"],
        soft_skills=["Communication"],
        recommended_hire=True,
        holistic_adjustment=0,
        holistic_adjustment_reason="Experience excluded from score",
        graded_questions=[
            GradedQuestion(
                question_index=1,
                question_text="Q1",
                question_type="theoretical",
                difficulty="easy",
                candidate_answer="A1",
                score=80,
                feedback="Good",
            ),
            GradedQuestion(
                question_index=2,
                question_text="Q2",
                question_type="problem_solving",
                difficulty="medium",
                candidate_answer="A2",
                score=90,
                feedback="Very Good",
            ),
            GradedQuestion(
                question_index=3,
                question_text="Q3",
                question_type="experience",
                difficulty="medium",
                candidate_answer="A3",
                score=30,
                feedback="Vague background, but does not affect tech score",
            ),
        ]
    )

    service.llm.generate = AsyncMock(return_value=mock_feedback.model_dump_json())

    request = AnalyzeVettingRequest(
        freelancer_id="free-1",
        job_title="Dev",
        job_description="Desc",
        job_skills=["Python"],
        qa_pairs=[
            QuestionAnswerPair(question_index=1, question_text="Q1", candidate_answer="A1"),
            QuestionAnswerPair(question_index=2, question_text="Q2", candidate_answer="A2"),
            QuestionAnswerPair(question_index=3, question_text="Q3", candidate_answer="A3"),
        ]
    )

    result = asyncio.run(service.analyze_vetting(request))
    assert result.score == 86
