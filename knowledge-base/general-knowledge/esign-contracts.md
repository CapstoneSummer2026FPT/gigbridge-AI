---
title: "GigBridge E-Sign Contracts (esign, e-sign)"
source: "https://gigbridge.id.vn/contracts/esign"
description: "Repository and status view for electronic contract documents, digital signature workflow, and eSign agreements."
keywords: "esign, e-sign, digital signature, contract signing, electronic signature, ky ten hop dong"
---

# E-Sign Contracts (esign, e-sign)

E-Sign Contracts (esign, e-sign) is the participant's document-oriented view of agreements that require or contain electronic digital signatures. It complements the general Contracts list by emphasizing document availability and who has signed.

---

## 1. Access & Purpose

- **Route**: `/contracts/esign`
- **Access**: Authenticated contract participants.
- **Purpose**: Locate e-signable agreements, check signature progress, open the relevant contract, and continue a required signing action.

The page handles loading, empty, and failed-document states separately. A missing generated document can mean that the signing sequence has not yet produced it, not that the underlying contract is absent.

---

## 2. Document Information

Entries associate the e-sign document with its contract/project, parties, creation or update information, and signature status. The current user's status is distinguished from the other party's status so `I signed` is not confused with `fully signed`. When a signed or generated document is available, participants can open the document workflow or return to Contract Details for the complete agreement context.

---

## 3. Actions by State

1. **Signature required** — open the contract signature or individual document-signing page.
2. **Current user signed** — view status and wait for the counterpart where necessary.
3. **Both parties signed** — continue to escrow funding for the client, wait for funding as the freelancer, or open the active workspace.
4. **Completed/unavailable** — preserve document access where supported without offering an invalid signing action.

---

## 4. Relationship to the Contract

An e-sign record documents consent; it does not replace contract state. Budget, dates, scope, milestones, escrow, work delivery, disputes, and reviews remain in Contract Details and the project workspace. Users should confirm the contract title and parties before signing, especially when more than one agreement is awaiting action.
