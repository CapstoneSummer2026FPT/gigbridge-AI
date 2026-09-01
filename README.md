# GigBridge AI Server

This is the independent AI microservice for the **GigBridge** freelance marketplace. Built using Python and **FastAPI**, it provides core intelligent features (Job Post Generation, AI Interviews with voice processing, Talent Matching, and Analytics) via secure REST API endpoints.

---

## 🚀 Key Features

1.  **AI Job Post Creation**: Generates styled markdown job descriptions based on title, category, and skills.
2.  **AI Interview**: Conducts mock interviews supporting voice transcripts (via OpenAI Whisper) and dynamic questions spoken back (via ElevenLabs TTS).
3.  **AI Talent Matching**: Semantically parses profiles and matches them to open job descriptions using vector embeddings.
4.  **AI Analysis**: Generates analytics and work insights on project files, milestones, and dispute logs.
5.  **LLM Router/Gateway**: A self-contained router managing model fallbacks (`OpenAI` -> `Gemini` -> `Claude` -> `Local Ollama`) in case of service downtime.
6.  **Custom RAG Pipeline**: In-memory and disk-persisted vector searches using Chroma DB.

---

## 🛠️ Tech Stack
*   **Web Framework**: FastAPI
*   **Web Server**: Uvicorn
*   **Database**: Chroma DB (Vector database)
*   **Language Models Client**: LiteLLM / Custom httpx wrappers (Google Gemini, OpenAI GPT, Anthropic Claude, Local Ollama)
*   **Voice Processing**: ElevenLabs API (Text-to-Speech), OpenAI Whisper API (Speech-to-Text)

---

## 📋 Running the Server

### 1. Prerequisite Setup
Clone the repository and copy the environment variables template:
```bash
cp .env.example .env
```
Open `.env` and fill in your API keys (`GEMINI_API_KEY`, `OPENAI_API_KEY`, `ELEVENLABS_API_KEY`, etc.) and set the `AI_SERVER_API_KEY` for verification.

Production deployments must also set `APP_ENV=production`, use a unique
non-placeholder `AI_SERVER_API_KEY`, and provide Redis 6.2 or newer (native
`GETDEL` is required for atomic interview confirmation).

### 2. Local Setup
We recommend using a Python virtual environment (Python 3.11+):
--- câu lệnh trỏ tới python lib

$env:Path = "C:\Users\OS\AppData\Local\Programs\Python\Python311;C:\Users\OS\AppData\Local\Programs\Python\Python311\Scripts;" + $env:Path


# 1. Create virtual environment
python -m venv .venv

# 2. Activate virtual environment
.\.venv\Scripts\Activate.ps1

# 3. Install required packages
pip install -r requirements.txt

# 4. Copy .env file
Copy-Item .env.example .env

# 5. Run the AI server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
Visit `http://localhost:8000/docs` to view the interactive Swagger API documentation.

### 3. Docker Setup
Build and run the container:
```bash
# Build the Docker image
docker build -t gigbridge-ai-server .

# Run the container
docker run -p 8000:8000 --env-file .env gigbridge-ai-server
```

---

## 🔒 Security & Client Authentication
All API endpoints are protected using a header-token authorization check. Clients (such as the C# backend) must attach the `X-API-Key` header with the token set in `AI_SERVER_API_KEY`.
```http
X-API-Key: your-secure-shared-api-key-here
```

Starting an interview also returns an `audio_access_token`. Send it as
`X-Session-Token` when polling the session's question-audio endpoint; the
shared server API key alone does not authorize access to candidate audio.
