---
title: "GigBridge Project Workspace"
source: "https://gigbridge.id.vn/workspace/:contractId"
description: "Shared client-freelancer workspace for contract execution and issue reporting."
---

# Project Workspace

The Project Workspace is the operational center of an active contract. It combines the participant/project list, milestone execution, shared chat and files, deliverable handoff, issue reporting, dispute awareness, completion, and reviews in one contract-scoped page.

---

## 1. Layout & Access

- **Route**: `/workspace/:contractId`
- **Access**: The contract's client and freelancer.
- **Desktop**: Project list, milestone panel, and chat/files panel are shown together.
- **Mobile**: Separate List, Milestones, and Chat/Files views keep the same project selected.

Completed workspaces become view-oriented, and an active dispute locks ordinary interaction while linking to Dispute Details.

---

## 2. Milestone Execution

Each milestone shows title, description, amount, released amount, due/completion dates, status, and work items. Freelancers can start or complete work items, add a progress note, submit an eligible milestone, and request an early start for a pending next milestone. Every work item must be complete before workspace submission is allowed. Clients can approve or reject an early-start request and open submitted work in the milestone review page.

Approved milestones can expose early withdrawal when the approval threshold and contract cap permit it. The confirmation dialog shows the available amount and blocks duplicate requests.

---

## 3. Chat, Files & Handoff

The Chat tab keeps participant messages and structured report-system events in the contract context. The Files tab collects shared attachments and product-handoff material. Deliverable submission can use an uploaded file or supported link/source plus a description. Upload and send controls are disabled when the workspace is locked.

---

## 4. Issues, Completion & Reviews

Participants can raise a contract report for payment, milestone, delay, quality, communication, scope, or another issue. The counterpart can accept, explain, propose a resolution, or reject it; reports move through pending, waiting-confirmation, resolved, or escalated states. Escalation creates a formal dispute and routes to its case.

Ending a project requires milestones to be submitted or approved; full completion requires all milestones approved. The confirmation shows the completed job amount and calculated service fee. When the resulting contract permits a review, GigBridge opens or later re-prompts the role-specific review form, while remembering a dismissal for that user and contract.
