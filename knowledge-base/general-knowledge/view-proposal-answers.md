---
title: "GigBridge View Proposal Answers"
source: "https://gigbridge.id.vn/proposals/:proposalId/answers"
description: "Ordered review of screening questions and answers saved with a selected proposal."
---

# View Proposal Answers

View Proposal Answers loads the selected proposal and its screening-answer records in parallel. It presents the stored result in question order and identifies required, optional, and unanswered entries.

---

## 1. Page Access & Context

- **Route**: `/proposals/:proposalId/answers`
- **Access**: Authenticated participants authorized to view the proposal.
- **Header**: Shows the related job title and current proposal status.
- **Back Action**: Returns to the previous proposal context.

If proposal or answer loading fails, the page shows the error instead of partial content that could be mistaken for a complete submission.

---

## 2. Answer Presentation

- Questions are sorted by `orderIndex`.
- Each card shows the question order and text.
- Required and Optional badges preserve the Client's configuration.
- The saved answer is shown as text.
- Optional questions without text display No Answer Provided rather than inventing a response.

---

## 3. Edit Eligibility

When the proposal status still permits editing, an Edit Answers action returns to the question route with the proposal and job IDs. Later proposal states remain review-only.

Changing an answer requires saving through the question workflow; viewing the page does not alter the proposal.

---

## 4. Empty & Security States

An empty list can mean the proposal has no stored screening answers. Unauthorized access, a missing proposal, or a failed backend request is handled as an error and does not expose another user's answer data.
