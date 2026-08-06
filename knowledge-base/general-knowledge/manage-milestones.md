---
title: "GigBridge Manage Contract Milestones"
source: "https://gigbridge.id.vn/contracts/:contractId/milestones"
description: "Shared milestone status, funding, delivery, approval, and change-control page."
---

# Manage Contract Milestones

Manage Milestones turns a contract budget into dated, trackable units of work. The page serves both setup and execution, but editing, delivery, approval, and withdrawal controls appear only for the appropriate role and contract state.

---

## 1. Modes & Permissions

- **Route**: `/contracts/:contractId/milestones`
- **Setup modes**: `?mode=jobpost-setup` completes the draft created during job posting; `?mode=contract-edit` prepares details for freelancer review.
- **Editable statuses**: A client can change milestones while the contract is `Pending Freelancer Selection`, `In Negotiation`, or `Pending Contract Details`.
- **Execution**: On an active contract, freelancers submit eligible work and clients review submitted work.

---

## 2. Milestone Fields & Validation

Each milestone requires a title, a positive GigCoin amount, and a due date later than today. New items begin as `Pending`. The budget summary compares total contract value, allocated milestone value, and remaining value. A milestone cannot exceed the unallocated budget.

In setup/edit modes, the page enforces the contract total. A draft can be saved for later, but submitting details to the freelancer requires the milestone sum to match the total contract budget exactly.

---

## 3. Lifecycle

Milestones move through `Pending`, `In Progress`, `Submitted`, and `Approved`. During an active contract:

- A freelancer can submit deliverables for an `In Progress` milestone.
- A client can review an item in `Submitted` state.
- Approved items expose released amount information.
- Editable milestones retain update controls only where contract rules permit them.

---

## 4. Early Withdrawal

An approved milestone may expose early withdrawal to its freelancer. Availability depends on active-contract status, approved-milestone threshold, the amount already released, and the contract-level early-withdrawal cap. The confirmation dialog shows the currently available amount. Repeated requests are blocked while one is processing, and a backend rejection is displayed against that milestone.

Milestone approval and withdrawal are separate: approval recognizes delivery, while withdrawal moves only the amount currently eligible under financial policy.
