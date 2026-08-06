---
title: "GigBridge Job E-Sign Setup"
source: "https://gigbridge.id.vn/jobs/post/esign"
description: "Electronic-signature configuration used while preparing a client project request."
---

# Job E-Sign Setup

Job E-Sign Setup records the client's acknowledgement of the draft contract created during job posting. It preserves the job and contract-form context from the prior steps and routes the client into milestone allocation after a successful signature.

---

## 1. Access & Recovery

- **Route**: `/jobs/post/contract/esign` (the router path used by the posting flow).
- **User**: Client preparing a job post.
- **Required context**: Created job-post ID, job data, and contract form.
- **Missing ID**: Redirects to the first job-post step.

The page also checks whether the client has already signed and tries to load the draft contract associated with the job post. An already-signed document can proceed to milestone setup without collecting another signature.

---

## 2. Review & Signing

The client reviews the prepared job/contract information, captures the required e-signature, and confirms having read and agreed to the displayed terms. Processing and error states prevent accidental repeated requests. Going back preserves navigation state to the contract-details step.

---

## 3. Backend Contract Link

After e-sign completion, the page fetches the draft contract by job-post ID. If it is immediately available, its ID is stored for the next route. If the lookup is delayed, the signing success is still shown and the client can return to My Jobs; the interface does not invent a contract ID.

---

## 4. Next Step

The success action normally opens `/contracts/:contractId/milestones?mode=jobpost-setup`. There the client creates allocations whose sum exactly matches the contract budget and completes setup. The alternative is to return to My Jobs.

This stage is not the later bilateral contract-signature workflow. It prepares a client-side draft linked to the job post; freelancer selection, negotiation, counterpart signature, and escrow funding remain separate lifecycle events.
