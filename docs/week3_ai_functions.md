# Week 3: Core AI Use Cases & Web Functions

This guide details the implementation of the four core AI endpoints in the microservice.

## 1. AI Job Post Creator
Exposes `POST /api/v1/ai/job-posts/generate`.
*   Uses a compiled prompt template (`job_posts.txt`) to outline sections: *About the Role*, *Responsibilities*, *Requirements*, and *What We Offer*.
*   Persists the generated job post payload in local domain memory.

## 2. AI Interview Simulator (with Speech STT/TTS)
Exposes endpoints for chat-based screening:
*   `POST /api/v1/ai/interviews/start`: Generates the first recruiting question. If mode is `voice`, calls ElevenLabs API to synthesize speech and returns it as base64 audio.
*   `POST /api/v1/ai/interviews/submit`: Processes user text responses and returns the next question or compiles a final hiring decision.
*   `POST /api/v1/ai/interviews/submit-audio`: Processes voice recordings (MP3/M4A). Uses OpenAI Whisper to transcribe response, then submits text to progress interview state.

## 3. AI Talent Matching
Exposes `POST /api/v1/ai/matching/recommend`.
*   Queries candidates in vector DB using semantic queries compiled from job posts.
*   Runs LLM profile analysis to return list of matched skills, missing skills, and detailed match reasoning.

## 4. AI Analysis
Exposes `POST /api/v1/ai/analysis`.
*   Evaluates dispute messages, milestone status checks, and portfolio reviews.
*   Outputs structured JSON containing Markdown summaries, risk levels (low/medium/high), and actionable recommendations.
