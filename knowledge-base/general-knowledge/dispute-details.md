---
title: "GigBridge Dispute Details"
source: "https://gigbridge.id.vn/contracts/:contractId/disputes/:disputeId"
description: "Participant case page for a contract dispute, evidence, messages, and resolution state."
---

# Dispute Details

Dispute Details is the case record used when a contract issue has been escalated beyond ordinary workspace resolution. It preserves the claim, requested outcome, evidence from each side, case communication, deadlines, and the platform's final resolution.

---

## 1. Access & Case Identity

- **Route**: `/contracts/:contractId/disputes/:disputeId`
- **Access**: Authorized contract participants and administrators.
- **Loaded together**: The dispute and its parent contract are checked so mismatched or unauthorized identifiers do not expose a case.
- **Issue types**: Payment, milestone, delay, poor quality, communication, scope change, and other.
- **Urgency**: Normal, high, or critical.

---

## 2. Claim Summary

The page shows the initiator, reason/description, desired resolution, claimed amount when supplied, linked milestone when relevant, creation/update dates, and current status. Statuses include `Open`, `Waiting Admin`, `Under Review`, `Waiting Evidence`, `Decision Pending`, `Resolved`, and `Closed`.

---

## 3. Evidence & Communication

Evidence is grouped by participant role. Files use secured download URLs rather than exposing storage paths. If an administrator requests more evidence, the page shows the target party, deadline, and whether the request was fulfilled. Upload controls are available only while the case status accepts evidence. A dispute-specific conversation area keeps case messages with the record.

---

## 4. Resolution

Possible recorded outcomes are `Client Favored`, `Freelancer Favored`, `Split`, `Dismissed`, or no decision yet. Resolved and closed cases retain the evidence and decision for reference but stop presenting active-case actions. The page does not promise a particular refund or release solely from the displayed label; financial effects follow the recorded backend resolution and wallet transaction trail.

Loading, permission, unavailable-evidence, and API error states are kept distinct so participants know whether a case is pending, inaccessible, or technically unavailable.
