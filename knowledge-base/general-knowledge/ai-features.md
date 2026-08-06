---
title: "GigBridge AI Features"
source: "Current frontend and AI service implementation"
description: "Current user-facing AI assistant, job drafting, talent matching, and voice interview capabilities."
---

# AI Features

## AI Assistant

The in-app assistant answers questions about GigBridge by querying the `general-knowledge` vector collection. It uses conversation history and retrieved Markdown context, but it cannot execute account, wallet, proposal, or contract actions.

## AI-Assisted Job Drafting

Eligible Client Premium users can describe a project in a prompt. The AI proposes structured job fields such as title, category, description, skills, and related planning content. The result remains a client-reviewed, editable draft; it is not published automatically.

## Smart Talent Matching

Client Premium users can choose an open job and generate a ranked freelancer shortlist. The current matching service combines semantic retrieval with deterministic evidence/scoring. Results expose factors such as relevant skills/categories, track record, and platform activity instead of asking a generative model to invent candidate facts.

## AI Voice Interview

Eligible freelancer applications can use a voice-led interview based on the job's configured questions. The browser records an answer, speech-to-text produces a transcript for review, and text-to-speech plays interviewer prompts. Microphone permission and a supported browser are required.

Earlier documentation referred to user-facing plagiarism/focus-loss monitoring and an `/admin/cheating` screen. Those are not present in the current router and should not be presented as current functionality.
