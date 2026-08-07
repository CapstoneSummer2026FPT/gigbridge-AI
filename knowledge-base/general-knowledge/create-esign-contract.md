---
title: "GigBridge Create E-Sign Contract"
source: "https://gigbridge.id.vn/contracts/create/:proposalId"
description: "Create a contract from an accepted or eligible proposal."
---

# Create E-Sign Contract

This client workflow converts a selected proposal into a structured contract and sends it into the signature process. Proposal and job information are used as the starting point, but the client must confirm complete, internally consistent contract terms.

---

## 1. Access & Prefilled Context

- **Route**: `/contracts/create/:proposalId`
- **User**: The hiring client for an eligible proposal.
- **Prefill**: The freelancer, proposal/job context, title such as `Contract for [job title]`, scope description, and proposed milestones are loaded when available.
- **Default payment language**: Escrow is assigned per milestone and released after client approval.

---

## 2. Four-Step Workflow

1. **Review Proposal** — confirm the freelancer, job, proposed price, and submitted plan.
2. **Set Terms** — enter the contract title, budget, scope, payment terms, dates, and milestone schedule.
3. **Preview PDF** — inspect the generated agreement and clauses as the parties will see them.
4. **Send for Signing** — create the contract and issue it to the participants for e-signature.

---

## 3. Contract Validation

- Title must contain 5–255 characters.
- Budget must be greater than zero.
- Scope, payment terms, start date, and end date are required.
- The end date must be later than the start date.
- At least one milestone is required.
- Every milestone needs a title, future/valid due date, and positive amount.
- The milestone sum cannot exceed the contract budget.

Errors remain attached to the current step so invalid terms are not silently turned into a document.

---

## 4. Creation Result

On submission, GigBridge first creates the contract and then requests the e-signature workflow. The user is redirected to the new Contract Details page. Creation alone does not mean the contract is active: the required parties must sign, and the client must fund escrow when the contract reaches that state.
