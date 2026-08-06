---
title: "GigBridge Contracts"
source: "https://gigbridge.id.vn/contracts"
description: "Role-aware list and management entry point for GigBridge contracts."
---

# Contracts

The Contracts page is the signed-in user's index of formal client–freelancer agreements. Its cards and actions differ by role and contract state, allowing users to find agreements that need signing, funding, delivery, approval, or review.

---

## 1. Access & Organization

- **Route**: `/contracts`
- **Access**: Authenticated clients and freelancers with an available profile.
- **Tabs**: Active, pending, and completed agreements are separated so unfinished setup is not mixed with live work.
- **Search**: Contracts can be matched by project title, description, counterparty information, or related profile identifier.
- **Sort**: Results can be ordered by date or contract value.

The freelancer view paginates the results at five contracts per page. Loading, API failure, and empty-result states are rendered separately.

---

## 2. Contract Cards

Each entry identifies the project, counterparty, current contract status, value, dates, and milestone progress. Progress is based on approved milestones rather than merely uploaded deliverables. Expanding a contract reveals milestone titles, amounts, due dates, and statuses.

---

## 3. Role-Aware Actions

- **Pending signature**: Open the contract or signature workflow.
- **Pending escrow**: The client proceeds to funding; the freelancer sees that funding is awaited.
- **Active**: Open Contract Details or the shared workspace. Freelancers can submit eligible milestones, while clients can review submitted milestones.
- **Completed**: Open the final record and leave a review when the contract permits it.

Client management controls may also expose editable details and milestone setup during negotiation/setup statuses. Actions are derived from backend status and ownership, so a visible contract does not automatically grant every operation.

---

## 4. Status Meaning

Pending contracts are still completing terms, signatures, or escrow. Active contracts support work execution. Completed contracts are historical but remain accessible for their financial and review records. Disputed or otherwise restricted agreements link into their issue workflow instead of presenting ordinary work controls as though they remain available.
