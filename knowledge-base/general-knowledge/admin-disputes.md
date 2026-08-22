---
title: "GigBridge Admin Dispute Arbitration"
source: "https://gigbridge.id.vn/admin/disputes"
description: "Administrator dispute management dashboard for evaluating contract disputes, inspecting workspace logs, reviewing code deliverables, and issuing binding escrow rulings."
---

# Admin Dispute Arbitration

The Admin Dispute Arbitration page is the central moderation portal where administrators investigate contractual disagreements between Clients and Freelancers, review evidence, and distribute escrow funds.

---

## 1. Page Access & Arbitration Queue

- **Route**: `/admin/disputes`
- **Access**: Restricted to `Admin` role.
- **Queue Statuses**:
  - **Needs Arbitrator**: Unassigned dispute cases awaiting administrator takeover.
  - **In Review**: Disputes currently under investigation by an assigned administrator.
  - **Awaiting Party Input**: Cases pending response or proof upload from Client or Freelancer.
  - **Resolved**: Settled cases with finalized escrow distribution record.

---

## 2. Evidence Inspection Tools

Administrators are provided with full investigation access:
- **Dispute Statement**: Claims and counter-claims submitted by both parties.
- **Contract & Milestone Specifications**: Original agreed scope, deliverable criteria, and milestone amounts.
- **Workspace Activity & Chat Audit**: Complete transcript of contract workspace chat messages, file sharing logs, and revision requests.
- **Submitted Deliverables**: Access to uploaded ZIP files, code repositories, and demo URLs submitted by the Freelancer.

---

## 3. Escrow Settlement Rulings

The administrator can issue binding financial settlements:
- **Full Release to Freelancer (100%)**: Transfers 100% of the disputed milestone escrow to the Freelancer.
- **Full Refund to Client (100%)**: Refunds 100% of the disputed milestone escrow back to the Client's wallet.
- **Partial Split (Custom %)**: Allocates a user-defined percentage split (e.g., 60% Freelancer / 40% Client).

---

## 4. Elo & Compliance Enforcement

- **Elo Penalty Assignment**: Option to apply automated or custom Elo score penalties to the losing or non-compliant party.
- **Resolution Summary**: Formal ruling explanation logged to both parties and archived in contract records.
