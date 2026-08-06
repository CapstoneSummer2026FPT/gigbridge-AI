---
title: "GigBridge Job Contract Setup"
source: "https://gigbridge.id.vn/jobs/post/contract"
description: "Client page for associating contract terms with a project request."
---

# Job Contract Setup

Job Contract Setup is the second stage of the client posting flow. It converts the newly created job-post data into initial contract terms before the client signs the draft and defines its milestone schedule.

---

## 1. Entry Requirements

- **Route**: `/jobs/post/contract`
- **User**: Client.
- **Required navigation state**: The preceding job-post step must supply both the created job-post identifier and its job data.
- **Recovery**: If that state is missing, GigBridge displays an error and redirects to `/jobs/post` rather than creating an unlinked contract.

---

## 2. Contract Fields

The form asks for:

- **Title** — the working contract title.
- **Description** — the initial scope/context.
- **Total budget** — prefilled from the job's maximum budget when present, otherwise its minimum budget.
- **Start date** — initialized from the creation-stage context and editable in the form.
- **End date** — the intended contract deadline.

Title, budget, and end date are mandatory before the client can continue. The continue action remains disabled when those fields are empty, and submission repeats the validation.

---

## 3. Navigation & State

Going back returns to job creation with the existing job data and identifier so the client can revise the listing. Continuing sends the same job information plus the contract form to `/jobs/post/contract/esign`; it does not yet activate a contract.

---

## 4. Relationship to Later Steps

This page sets headline terms only. The next page captures the client's signature and creates or discovers the backend draft contract. After signing, the client proceeds to milestone setup in `jobpost-setup` mode, where allocations must match the contract budget before the posting workflow is complete. A freelancer is selected and participates in the later negotiation/signature lifecycle; this initial client signature should not be described as a mutually signed, funded agreement.
