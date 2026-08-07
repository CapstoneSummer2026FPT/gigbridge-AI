---
title: "GigBridge E-Sign Document Signing"
source: "https://gigbridge.id.vn/contracts/:contractId/documents/:documentId/sign"
description: "Electronic signing pad for an individual GigBridge contract document."
---

# E-Sign Document Signing

This page signs one generated document belonging to a specific contract. It gives the signer a document review, signature capture, confirmation, and completion trail rather than treating a button click as sufficient legal consent.

---

## 1. Document Verification

- **Route**: `/contracts/:contractId/documents/:documentId/sign`
- **Access**: An authorized signer for the parent contract.
- **Checks**: Both identifiers must resolve, the document must belong to the contract, and the current user must be eligible to sign.

The review step shows the document code/ID, title, creation and expiration information, instructions, and exported PDF when available. The user can copy the document identifier and inspect the PDF before continuing. A decline option is available where the document state permits it.

---

## 2. Signature Capture

The capture experience offers supported methods such as drawing, typing, or initials. The signer can clear and replace the current mark before confirmation. Already-signed documents suppress another signing submission and direct the user to the recorded status.

---

## 3. Confirmation & Audit Context

Before final submission, the page previews the selected signature and identifies the signing user and timestamp/device audit context. It explicitly explains that the action is legally binding. The signer must confirm the final action; incomplete capture or expired/ineligible documents cannot be submitted.

---

## 4. Completion

After a successful response, the document displays a completion state and signature/audit information. Depending on the counterpart's status and the parent contract, the next step may be waiting for another signature, returning to Contract Details, funding escrow, or opening the workspace.

This individual-document flow should not be confused with the contract-level signature page: both reference the same agreement lifecycle, while this route addresses a particular generated e-sign document.
