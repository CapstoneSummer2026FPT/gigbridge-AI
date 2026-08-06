---
title: "GigBridge AI Interview"
source: "https://gigbridge.id.vn/ai-interview/:jobPostId"
description: "Voice-led job interview workflow for eligible freelancer applications."
---

# AI Interview

**Routes:** `/ai-interview`, `/ai-interview/:jobPostId`

**Access:** Signed-in users with completed setup; completing a job interview is a freelancer application flow.

An interview requires a selected job that has interview questions. The AI interviewer plays each question aloud while the question text remains hidden. The freelancer presses **Answer question**, speaks naturally, and finishes manually or after the supported silence countdown.

GigBridge records the answer with browser microphone permission, converts it to a read-only transcript, and lets the user speak again before submitting. After submission, the next question plays automatically until the interview is complete.

A current browser with microphone recording support is required. Denied permission, missing audio, transcription errors, and voice playback failures produce retry guidance. Completed responses are submitted with the application, and decisions are communicated later through in-app/email updates.
