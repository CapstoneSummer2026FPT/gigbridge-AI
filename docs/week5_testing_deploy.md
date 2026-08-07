# Week 5: Testing, Docker, & Deployment

This guide outlines the validation and deployment workflows implemented in Week 5.

## 1. Testing Strategy
We use `pytest` and `httpx.AsyncClient` to run integration tests against the endpoints.
*   Test coverage is focused on verifying that request validation works (e.g. throwing HTTP 422 on bad inputs), verifying header token verification (HTTP 401 on missing key), and verifying fallback routing in the LLM Gateway.

## 2. Docker Containerization
The `Dockerfile` builds a lightweight image based on `python:3.11-slim`:
```dockerfile
FROM python:3.11-slim
WORKDIR /workspace
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 3. Microservice Deploy & Networking
*   **Internal Gateway**: In production, the API container is protected from public internet. The C# backend acts as a reverse proxy/orchestrator.
*   **Environment Settings**: Pass credentials (`OPENAI_API_KEY`, `GEMINI_API_KEY`, `ELEVENLABS_API_KEY`, `AI_SERVER_API_KEY`) securely via Docker Compose environment configurations or cloud vault managers.
*   **Docker Volumes**: Mount a persistent storage folder to `/workspace/chroma_db` inside the container to persist vector search collections.
