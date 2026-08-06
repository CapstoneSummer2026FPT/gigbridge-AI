---
title: "GigBridge Contract Signature Workflow"
source: "https://gigbridge.id.vn/contracts/:contractId/sign"
description: "Participant workflow for reviewing contract documents and completing required signatures."
---

# Contract Signature Workflow

This three-step flow lets the client and freelancer review the same agreement, draw a signature, accept the applicable GigBridge policy, and see what must happen after signing. It does not treat one party's signature as a fully active contract.

---

## 1. Eligibility & Steps

- **Route**: `/contracts/:contractId/sign`
- **Users**: The named client and freelancer.
- **Steps**: `Review Proposal` → `Proceed to Sign` → `Completed`.
- **Readiness**: The contract must be in a signable state. If the generated e-sign document is not yet available, the page explains that it will be generated when the first party signs.

---

## 2. Review Before Signing

The summary displays the document/project name, contract budget, milestone total, start and end dates, and linked client and freelancer profiles. It includes the contract scope and every milestone's sequence, title, due date, and amount. A warning appears when the milestone total differs from the contract total. When rendered contract HTML exists, it is shown in a sandboxed preview.

---

## 3. Capture & Consent

The signer draws on a 600 × 200 signature pad and can clear and redraw it. Submission remains disabled until a non-empty signature exists and the signer checks the consent box for the linked GigBridge policy version. The saved image includes its canvas dimensions. Duplicate-sign responses are handled as an already-completed signature rather than creating another record.

---

## 4. Completion & Next Step

After one signature, the page records it and waits for the counterpart. After both signatures, the contract moves to the appropriate next state:

- **Client**: Fund escrow when status is `Pending Escrow`.
- **Freelancer**: Wait for the client to fund escrow.
- **Both parties**: Open the workspace when the contract is `Active`.

The completion panel shows the document, current status, and next action. A recorded signature remains visible if the signer returns to the workflow.
