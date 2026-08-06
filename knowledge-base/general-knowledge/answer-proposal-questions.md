---
title: "GigBridge Answer Proposal Questions"
source: "https://gigbridge.id.vn/proposals/create/:jobPostId/questions"
description: "Timed Freelancer screening-question workflow with answer locking, review window, draft saving, and final proposal submission."
---

# Answer Proposal Questions

This page is a timed text-based screening interview attached to a saved proposal. It loads the job's ordered questions and existing answers, then locks questions one by one before opening a limited review period.

---

## 1. Page Access & Readiness

- **Route**: `/proposals/create/:jobPostId/questions`
- **Access**: Freelancers with completed setup and a saved proposal ID supplied in navigation state or `proposalId` query data.
- **Required Context**: Both proposal ID and job-post ID must be available.
- **Proposal Validation**: The saved proposal narrative and milestone data are checked before the timed interview can start.

Missing IDs or an incomplete proposal produce a readiness error instead of starting timers.

---

## 2. Timed Question Flow

1. Questions are sorted by their saved order.
2. Select Start Interview to request the server timer for the first unlocked question.
3. The current question displays its Required or Optional label and countdown.
4. Enter up to **4,000 characters**.
5. Continue locks the answer through the backend and starts the next question.
6. An unanswered optional question can be skipped; an unanswered required question cannot be completed normally.

The default local remaining time begins at 180 seconds and is synchronized with the expiration returned by the service. Timeout locks the question automatically.

---

## 3. Draft Saving

Before starting, Save as Draft can preserve proposal/question progress. During the active sequence, a non-empty current answer may be saved when supported, but the server question timer still controls whether that question is locked.

Saving an answer does not submit the full proposal.

---

## 4. Review Window

After all questions are locked, GigBridge requests an interview-review session. Reviewable answers can be edited only while that session remains unlocked and time remains.

- Required answers remain validated.
- The 4,000-character limit still applies.
- Expiry completes and locks the review session automatically.
- A Review Closed state prevents further editing.

---

## 5. Final Submission

The Submit Proposal button becomes available only after all questions are locked and the review session exists. It saves permitted review edits, completes the review, and advances the proposal according to the backend workflow.

This timed text screen is separate from the voice-led `/ai-interview/:jobPostId` experience.
