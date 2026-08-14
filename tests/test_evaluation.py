import pytest
from app.services.evaluator import EvidenceEvaluatorService
from evaluation.eval import evaluate_all_retrieval, evaluate_all_answers


def test_evidence_evaluator_basic():
    service = EvidenceEvaluatorService()
    source = "GigBridge requires electricians to hold NVQ Level 3 and ECS gold cards."
    evidence = "Electricians must possess NVQ Level 3 and an ECS gold card."

    res = service.evaluate(source, evidence)
    assert res.truth_percentage >= 50.0
    assert res.total_claims > 0
    assert "VERIFIED TRUE" in res.annotated_html or "PARTIAL" in res.annotated_html


def test_retrieval_benchmark_generator():
    items = list(evaluate_all_retrieval())
    assert len(items) > 0
    test, result, prog = items[0]
    assert 0.0 <= result.mrr <= 1.0
    assert 0.0 <= result.ndcg <= 1.0
    assert 0.0 <= result.keyword_coverage <= 100.0


def test_answer_benchmark_generator():
    items = list(evaluate_all_answers())
    assert len(items) > 0
    test, result, prog = items[0]
    assert 1.0 <= result.accuracy <= 5.0
    assert 1.0 <= result.completeness <= 5.0
    assert 1.0 <= result.relevance <= 5.0


def test_evaluate_dashboard_endpoint():
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    response = client.get("/evaluate")
    assert response.status_code == 200
    assert "GigBridge AI Microservice Evaluation Dashboard" in response.text

