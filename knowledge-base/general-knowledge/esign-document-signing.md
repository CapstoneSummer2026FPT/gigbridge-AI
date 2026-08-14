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

## 2. Interactive Signature Field Placement & Canvas Capture

The signature interface includes:
- **Signature Field Placement**: Visual overlay allowing signers to position, resize, or inspect dedicated signature boxes directly on PDF document pages.
- **Canvas Signature Pad**: HTML5 drawing pad supporting freehand signature drawing, typed signatures with stylized fonts, or saved digital signature images.
- **html2pdf Rendering**: Renders the complete legal contract contract into vector-accurate PDF pages with embedded CSS layout.

---

## 3. Digital Certificate & Audit Hash Generation

Before final submission, the system generates:
- **SHA-256 Signature Hash**: Cryptographic hash embedding user ID, timestamp, IP address, and signature coordinates into the PDF document metadata.
- **Digital Audit Trail Certificate**: Generates a tamper-evident audit log appended to the PDF file.
- **Automated Mail Dispatch**: Dispatches signed PDF contract copies to both Client and Freelancer email addresses upon final multi-party completion.

---

## 4. Completion

After a successful response, the document displays a completion state and signature/audit information. Depending on the counterpart's status and the parent contract, the next step may be waiting for another signature, returning to Contract Details, funding escrow, or opening the workspace.

This individual-document flow should not be confused with the contract-level signature page: both reference the same agreement lifecycle, while this route addresses a particular generated e-sign document.
