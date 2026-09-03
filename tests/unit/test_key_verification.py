import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings

client = TestClient(app)

def test_verify_key_success():
    """Test that verify-key endpoint returns 200 when correct X-API-Key is passed."""
    key = settings.AI_SERVER_API_KEY if settings.AI_SERVER_API_KEY else "test-key"
    settings.AI_SERVER_API_KEY = key

    response = client.post("/api/ai/verify-key", headers={"X-API-Key": key})
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["success"] is True
    assert json_data["data"]["valid"] is True

def test_verify_key_invalid():
    """Test that verify-key endpoint fails when wrong X-API-Key is passed."""
    settings.AI_SERVER_API_KEY = "valid-secret-key"
    response = client.post("/api/ai/verify-key", headers={"X-API-Key": "wrong-key"})
    assert response.status_code in (401, 403)

def test_verify_key_missing_header():
    """Test that verify-key endpoint fails when X-API-Key header is missing."""
    settings.AI_SERVER_API_KEY = "valid-secret-key"
    response = client.post("/api/ai/verify-key")
    assert response.status_code in (401, 403)
