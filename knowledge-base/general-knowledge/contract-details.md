---
title: "GigBridge Contract Details"
source: "https://gigbridge.id.vn/contracts/:contractId"
description: "Participant view of contract terms, signing, milestones, and dispute state."
---

# Contract Details

Contract Details is the authoritative participant view of an agreement between a client and freelancer. It brings together the commercial terms, parties, milestones, signatures, audit events, and current issue state so the next action can be selected from the contract's real status.

---

## 1. Access & Data Loading

- **Route**: `/contracts/:contractId`
- **Access**: The contract's client, freelancer, and authorized administrators. Other users receive an access-denied state.
- **Loaded records**: Contract, milestone list, audit trail, and any active dispute are fetched for the selected contract.
- **Error handling**: Missing identifiers, inaccessible contracts, and failed requests are displayed as explicit loading or error states.

---

## 2. Contract Record

The page shows the project or contract title, description/scope, total budget, start and end dates, client and freelancer identities, and the current contract status. Milestones expose their title, amount, due date, delivery state, and progress. The timeline adds lifecycle events such as creation, signatures, activation, and completion; a completed contract records that its milestones were approved and paid.

---

## 3. State-Aware Actions

Actions are intentionally conditional:

- A participant can open the signing workflow while a signature is required.
- Once both signatures are recorded, a client may be directed to fund escrow while the freelancer waits.
- An active contract opens its workspace, milestone delivery, approval, and milestone-management tools.
- Eligible completed work exposes the review action.
- An existing active dispute is surfaced and links to the case rather than encouraging a duplicate case.

The client can manage contract details or milestones only in the statuses where the backend permits changes. The freelancer receives submission controls only for their own active contract and eligible milestones.

---

## 4. Legal & Financial Context

Contract status is distinct from milestone status. Signing records consent, escrow funding makes the agreed value available for protected work, submission asks for review, approval accepts delivery, and release/withdrawal moves funds under separate rules. Audit information and an active-dispute warning remain part of the record so participants can understand why an action is available or blocked.
