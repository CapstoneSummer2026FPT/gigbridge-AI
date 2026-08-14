---
title: "GigBridge Admin Contracts & E-Sign Templates"
source: "https://gigbridge.id.vn/admin/contracts"
description: "Administrator interface for auditing active contracts, e-sign document repositories, digital signature certificates, and legal template management."
---

# Admin Contracts & E-Sign Templates

The Admin Contracts & E-Sign Templates page allows administrators to audit contract execution status, inspect digital signature logs, review PDF contract renders, and manage standard legal template clauses.

---

## 1. Page Access & Routes

- **Routes**: `/admin/contracts` (`/admin/contract-audit`), `/admin/contracts/esign`, `/admin/contract-templates`.
- **Access**: Restricted to `Admin` role.

---

## 2. Contract Audit Repository (`/admin/contracts`)

- **Contract Search**: Search by Contract ID, Job Title, Client Name, or Freelancer Name.
- **Status Filter**: `Draft`, `Pending Signature`, `Active Escrow`, `Completed`, `Disputed`, `Terminated`.
- **Contract Inspection**:
  - **PDF Contract Document**: View generated PDF contract featuring digital signature overlays and timestamp hashes.
  - **Milestone Breakdown**: Escrow funding status, release timestamps, and deliverable review logs.
  - **E-Sign Signature Hashing**: Audit SHA-256 digital signature hashes, IP addresses, and sign timestamps for both Client and Freelancer parties.

---

## 3. E-Sign Repository & Document Templates (`/admin/contracts/esign` & `/admin/contract-templates`)

- **Standard Legal Clause Templates**: Admin interface to create, edit, or archive contract templates (e.g., Fixed Price Development Agreement, Hourly Retainer Agreement, NDA Addendum).
- **Signature Field Configuration**: Define standard signature anchor points, legal disclaimer text, and required signer roles.
- **System Versioning**: Manage legal template revision history and enforce current template versions on newly created contracts.
