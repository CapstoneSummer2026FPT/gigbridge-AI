---
title: "GigBridge AI Features"
source: "AI Service Architecture"
description: "Documentation on AI job posting, talent matching, mock voice interviews, analytics, and cheating/focus detection."
---

# AI Subsystem Features

GigBridge integrates an independent AI service (built on FastAPI) that provides core intelligence functions: automatic job posting, semantic candidate matching, mock voice interviews, work analysis, and anti-cheating tracking.

---

## 1. AI Job Post Creator

Clients can generate optimized job descriptions automatically.
* **Inputs**: The client inputs a job title, primary category, and required skills.
* **Processing**: The AI engine uses LLM templates to draft a structured, professional markdown job description detailing role responsibilities, deliverables, and skill expectations.
* **Workflow**: The client can review, edit, and publish the AI-generated description directly, saving drafting time.

---

## 2. AI Talent Matching

Our platform combines vector retrieval with deterministic feature scoring.
* **Embedding Model**: Trusted profile data (title, bio, taxonomy, skills, availability, location, and verified completed work) and job descriptions are converted into vector representations.
* **Vector Similarity**: The AI service queries a disk-persisted vector store (Chroma DB) to rank candidates by cosine similarity against open job requirements.
* **Algorithmic Reranking**: A versioned weighted algorithm scores role/domain, task, preferred-skill, and verified-work relevance without a generative LLM.
* **Recommendation**: The backend combines embedding and algorithm scores with authoritative platform evidence before returning explained matches.

---

## 3. AI Mock Voice Interview

Clients can request candidates to undergo automated screening.
* **Transcription (STT)**: The system listens to candidate spoken responses and converts voice to text using OpenAI Whisper API.
* **AI Evaluation**: The LLM processes the transcript to analyze accuracy and clarity, scoring candidate responses.
* **Voice Synthesis (TTS)**: The AI speaks questions back to the candidate dynamically utilizing the ElevenLabs Text-to-Speech API.

---

## 4. Work Analytics & Insights

The AI service assists in project tracking.
* **Code & File Auditing**: Analyzes project files and milestone updates.
* **Dispute Summarization**: Generates timeline audits of workspace logs, communication history, and milestone deliverables to assist administrators during dispute resolutions.

---

## 5. Anti-Cheating & Plagiarism Monitoring

To ensure assessment and interview integrity:
* **Browser Focus Loss Logs**: During AI interviews or skill tests, the frontend monitors browser focus events. If the candidate switches tabs, minimizes the window, or opens another application to search for answers, a focus loss event is recorded.
* **Plagiarism Audits**: If a candidate copy-pastes pre-written text, the platform logs the action.
* **Administrator Review Dashboard**: All cheating logs, page exit timestamps, and copy-paste events are recorded and displayed on the `/admin/cheating` screen for moderator audits.
