---
title: "GigBridge My Disputes"
source: "https://gigbridge.id.vn/disputes"
description: "Overview dashboard for Clients and Freelancers to review open, pending, and resolved contract disputes."
---

# My Disputes

The My Disputes page serves as the central hub for Clients and Freelancers to track active legal and delivery disagreements across their contracts. It allows participants to monitor evidence submissions, admin arbitration status, and escrow resolution payouts.

---

## 1. Page Access & Filter Tabs

- **Route**: `/disputes`
- **Access**: Authenticated Client and Freelancer roles.
- **Filter Tabs**:
  - **All Disputes**: Complete history of disputes filed or received.
  - **Active / Under Review**: Disputes currently being investigated by Admin arbitrators.
  - **Resolved / Closed**: Settled disputes with finalized escrow release or refund actions.

---

## 2. Dispute List Items

Each dispute entry card contains:
- **Dispute Title & ID**: Unique tracking identifier.
- **Associated Contract**: Contract title and job link.
- **Counterparty**: Name and role of the opposing party (Client or Freelancer).
- **Disputed Amount**: Total GigCoins held in escrow pending arbitration.
- **Filing Date**: Timestamp when the dispute was initiated.
- **Status Badge**: `Draft`, `Pending Evidence`, `In Review`, `Resolved - Refunded`, `Resolved - Released`, or `Resolved - Split`.

---

## 3. Dispute Actions & Detail Navigation

- **View Details**: Opens `/contracts/:contractId/disputes/:disputeId` to view chat logs, file evidence, and submit counter-statements.
- **Upload Additional Evidence**: Direct action to attach updated code deliverables, message records, or specification documents while the dispute remains in `Pending Evidence` state.
- **Cancel Dispute**: Allows the initiating party to withdraw the dispute prior to formal admin review if an informal agreement is reached.
