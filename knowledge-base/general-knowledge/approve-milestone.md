---
title: "GigBridge Approve Milestone"
source: "https://gigbridge.id.vn/contracts/:contractId/milestones/:milestoneId/approve"
description: "Client review and approval page for a submitted milestone deliverable."
---

# Approve Milestone

The Approve Milestone page is where a client examines submitted work and decides whether a milestone is ready for approval, needs revision, or requires a formal dispute. Approval is consequential: it accepts the submitted work and advances the contract payment workflow.

---

## 1. Access & Eligibility

- **Route**: `/contracts/:contractId/milestones/:milestoneId/approve`
- **User**: The client attached to the contract.
- **Required state**: The milestone must have been submitted for review. The contract and milestone identifiers must match.
- **Failure states**: Missing records, unauthorized access, or an ineligible milestone produce an error instead of approval controls.

---

## 2. Submission Review

The page identifies the contract and milestone and shows its value, due date, current status, and submission time. The client can read the freelancer's delivery description, completed work items, and progress notes. Uploaded attachments can be opened or downloaded so the actual deliverable can be checked before a decision is made.

---

## 3. Available Decisions

1. **Approve** accepts the milestone. The interface displays a success state and returns the client to the project workspace.
2. **Request revision** returns the milestone to `In Progress`. The client must enter revision notes of no more than 500 characters and select at least one work item that needs attention.
3. **Open dispute** starts the protected issue-resolution path when ordinary revision is not appropriate.

The page disables repeated actions while a request is processing and reports backend validation errors without implying that payment or status changed.

---

## 4. Payment Meaning

The milestone value is shown in GigCoin together with escrow context. Approval confirms work acceptance; escrow release and any withdrawal availability are governed by the contract payment workflow. A client should therefore inspect files, descriptions, and work-item completion before approving.
