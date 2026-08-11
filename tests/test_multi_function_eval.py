import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_multi_function_eval_endpoint():
    response = client.post("/api/ai/eval/multi-function")
    assert response.status_code == 200, f"Endpoint failed: {response.text}"

    data = response.json()
    assert "total_test_cases" in data
    assert "overall_system_mrr" in data
    assert "overall_system_ndcg" in data
    assert "overall_system_coverage" in data
    assert "functions" in data

    assert data["total_test_cases"] == 50
    assert len(data["functions"]) == 4
    assert data["overall_system_mrr"] > 0.8
    assert data["overall_system_ndcg"] > 0.8
