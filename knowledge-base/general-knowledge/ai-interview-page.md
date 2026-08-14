---
title: "GigBridge AI Interview"
source: "https://gigbridge.id.vn/ai-interview/:jobPostId"
description: "Voice-led Freelancer interview using streamed questions, microphone recording, transcription review, and sequential answer submission."
---

# AI Interview

The AI Interview is a voice-led screening workflow for a job with an interview definition and questions. It streams each question as audio, records the Freelancer's spoken response, transcribes it, and submits confirmed text sequentially.

---

## 1. Page Access & Session Start

- **Route**: `/ai-interview/:jobPostId`; `/ai-interview` also exists but requires a selected job context.
- **Access**: Authenticated users with completed setup; answering is a Freelancer application workflow.
- **Definition Context**: An interview definition ID can be supplied through URL or navigation state.
- **Start Validation**: Missing job, no predefined questions, failed session creation, or incomplete session data stops the interview with a specific error.

On success, the service returns a session ID, first question, question position/count, language, and audio-access token.

---

## 2. Question Playback

- The interviewer streams question audio through the backend.
- Question progress shows the current number and total count.
- Subtitle cues are synchronized with the playing audio rather than displaying the full question as a normal static form.
- Hear Again replays prepared audio; Retry Audio is available after a playback failure.
- If no audio token or stream is available, the page reports that voice playback is unavailable.

---

## 3. Recording an Answer

1. Select **Answer Question** and allow browser microphone access.
2. GigBridge chooses a supported `MediaRecorder` format such as WebM/Opus, WebM, or MP4.
3. Speak naturally while the timer and waveform are active.
4. Select Finish Answer, or allow the supported silence detection/recording limit to stop capture.
5. The recorded blob is uploaded for speech-to-text transcription.

The page releases the microphone and recording resources after each capture or cancellation.

---

## 4. Transcript Review, Gladia STT & Anti-Cheating Monitoring

- **Gladia STT Engine**: Audio blobs are transcribed using Gladia Speech-to-Text for ultra-fast, multi-lingual accuracy with custom phonetic hotword resolution.
- **ElevenLabs TTS**: Streams high-fidelity voice playback for interview question audio.
- **Anti-Cheating Tab-out Detection**: Tracks candidate window focus and tab switching during active interview sessions. Excessive tab-outs or browser unfocus events are logged to `/admin/cheating` for recruiter compliance review.
- **Record Again**: Discards the current transcript and resets recording state.
- **Submit Answer**: Submits confirmed transcript text to advance the interview session.
- When the service reports completion, the page moves to the Results stage.

Submitting the transcript—not merely recording audio—is what advances the interview.

---

## 5. Browser & Error Requirements

- Requires `getUserMedia` and `MediaRecorder` support.
- Denied microphone permission, unavailable input devices, recorder errors, empty audio, transcription errors, and answer-submission failures are handled separately.
- Audio playback may require browser permission or a user gesture.
- Leaving the screen stops active recording and audio playback.

Interview completion records screening responses; it does not automatically accept the proposal or create a contract.
