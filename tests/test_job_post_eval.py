import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_eval_job_post_endpoint():
    payload = {
        "client_prompt": "Cần tuyển Lập trình viên Python FastAPI để xây dựng hệ thống RAG Chatbot trong 2 tuần, ngân sách 500 GigCoins"
    }

    response = client.post("/api/ai/eval/job-post", json=payload)
    assert response.status_code == 200, f"Endpoint failed: {response.text}"

    data = response.json()
    assert "details" in data
    assert "hiring_plan" in data
    assert "jd_quality_score" in data
    assert "taxonomy_match_ok" in data
    assert "budget_clamped_ok" in data
    assert "summary_html" in data
    assert data["jd_quality_score"] > 0
