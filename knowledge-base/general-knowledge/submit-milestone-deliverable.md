---
title: "GigBridge Submit Milestone Deliverable"
source: "https://gigbridge.id.vn/contracts/:contractId/deliverables/:milestoneId"
description: "Freelancer submission page for evidence and outputs of completed milestone work."
---

# Submit Milestone Deliverable

This page lets the assigned freelancer submit a completed milestone for client review. It validates ownership, contract state, milestone relationship, description, and attachment before changing the milestone's workflow state.

---

## 1. Eligibility Checks

- **Route**: `/contracts/:contractId/deliverables/:milestoneId`
- **User**: The freelancer profile attached to the contract.
- **Contract**: Must be `Active`.
- **Milestone**: Must belong to the route's contract and be in a status accepted by the deliverable-submission rule.

An incorrect contract, another freelancer's contract, or an ineligible milestone shows a specific error rather than rendering a usable form.

---

## 2. Submission Fields

- **Description**: Required explanation of what was delivered, limited to 5,000 characters with a live counter.
- **Attachment**: One file is selected and submitted. Choosing another replaces the current selection; it can also be removed before sending.
- **Maximum size**: 100 MB.
- **Accepted extensions**: PDF, Word, Excel, PowerPoint, text, CSV, JSON, ZIP/RAR/7Z/TAR/GZ, JPG/JPEG/PNG/GIF/WebP, MP3/WAV, and MP4/WebM.

Unsupported extensions and oversized files are rejected before the API request. The page shows file name, size, and total selected size.

---

## 3. Submission Result

The request sends the description, selected file, and current delivery-date context for the named milestone. The submit button is disabled during processing. A backend failure leaves the user on the form with the returned error; it does not claim that the client received the work.

On success, a confirmation state appears and the user is returned to Contract Details after a short delay. Submission means the work awaits client review—it does not itself approve the milestone or release funds. The client can then approve, request revision, or escalate a dispute from the review workflow.
