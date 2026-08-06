---
title: "GigBridge Projects"
source: "https://gigbridge.id.vn/projects"
description: "List of contract-backed project workspaces available to the signed-in user."
---

# Projects

Projects is the launch page for ongoing client–freelancer collaboration. Unlike the broader Contracts list, it loads active contracts and treats each one as a workspace-ready project.

---

## 1. Access & Scope

- **Route**: `/projects`
- **Access**: Signed-in users; unauthenticated visitors are sent to Login.
- **Included records**: Contracts in `Active` status that belong to the current participant.
- **Purpose**: Re-enter execution work without navigating through negotiation, unsigned, or completed contracts.

---

## 2. Project Cards

Each project entry is backed by its contract and identifies the title, current status, counterparty, relevant dates/value, and workspace action. Counterparty names link to the appropriate client or freelancer profile where available. Opening the card routes to `/workspace/:contractId`, preserving the contract as the boundary for messages, files, milestones, and issue records.

---

## 3. Empty, Loading & Error States

Loading is shown while the user's active contracts are requested. Failed requests produce a recoverable error instead of an empty-project claim. When there are genuinely no active projects, the call to action depends on role:

- **Client**: Post a job to begin a hiring workflow.
- **Freelancer**: Browse jobs and submit a proposal.

Pending contracts do not appear as active workspaces merely because they exist. Users should check Contracts or My Jobs for agreements awaiting details, signatures, freelancer selection, or escrow.

---

## 4. Relationship to Completion

The workspace may offer project completion and reviews when milestone conditions are met. Once an agreement leaves the active state, its durable record remains available from Contracts and review/history pages even if it is no longer listed here. A disputed active workspace can also be locked while its dispute remains accessible through the contract-specific case route.
