---
title: "GigBridge Job Milestone Setup"
source: "https://gigbridge.id.vn/jobs/post/plan"
description: "Client planning step for baseline milestones, work items, acceptance criteria, and job interview questions."
---

# Job Milestone Setup

The Plan step turns the Client's draft into a measurable baseline delivery plan. It supports nested milestones and interview questions, compares the plan with the stated project budget and duration, and prepares the job for final review.

---

## 1. Page Access & Draft Requirement

- **Route**: `/jobs/post/plan`
- **Access**: Clients with completed setup and a job ID or job data from the creation flow.
- **Missing State**: Redirects to `/jobs/post` if no draft context is available.
- **Actions**: Back to Details, Save & Exit, or Review & Continue.

Leave protection can save, discard, or retain an in-progress draft.

---

## 2. Baseline Milestone Fields

Each milestone can include:

- Title and positive GigCoin amount.
- Estimated duration and unit.
- Optional or required deadline according to the current editor rules.
- Description and milestone outcome.
- Deliverables and acceptance criteria.
- Nested work-breakdown items with their own ordering and details.

Milestones can be added, removed, expanded, and reordered. Field-specific validation highlights the exact incomplete entry.

---

## 3. Budget & Duration Reconciliation

- **Milestone Plan Total**: Sum of milestone amounts.
- **Expected Budget**: Budget entered on the Details step.
- **Milestone Duration**: Combined planned duration compared with the job's estimated duration.

The wizard displays differences so the Client can reconcile the plan. These values describe the future project but do not fund escrow during job posting.

---

## 4. Interview Questions

- Questions are managed in an expandable section.
- Each question can be required or optional.
- Questions can be added, removed, and reordered.
- A character counter enforces the configured maximum question length.
- The summary reports how many non-empty questions were added.

These questions are later used in proposal screening and can support configured AI interview behavior.

---

## 5. Validation & Next Step

Review & Continue requires valid milestone titles and amounts and rejects overlong questions or other highlighted plan errors. On success, the draft is saved and the user moves to `/jobs/post/review`.

Saving the plan is not the same as publishing the job, signing a contract, or depositing milestone funds.
