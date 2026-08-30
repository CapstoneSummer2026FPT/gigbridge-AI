---
title: "GigBridge Receipts & Invoices"
source: "https://gigbridge.id.vn/receipts"
description: "Documentation on billing receipts, invoice generation, transaction breakdowns, payment statuses, and document downloads."
---

# Receipts & Invoices

The Receipts screen (`/receipts`) allows clients and freelancers to generate, view, and download official payment receipts and invoices for completed platform transactions (escrow funding, milestone payouts, subscription purchases, and GigCoin deposits).

---

## 1. Page Access & Authorization

- **Route**: `/receipts`
- **Access**: Authenticated Clients and Freelancers (role `Client` or `Freelancer`).
- **Data Scoping**: Users only see financial transactions associated with their own account ID or active contracts.

---

## 2. Receipt Details & Transaction Breakdown

Each itemized receipt includes:
- **Receipt ID & Reference Number**: Unique system transaction hash for accounting verification.
- **Timestamp**: Exact date and UTC/local time of transaction completion.
- **Contract / Milestone Link**: Direct reference to the parent contract or milestone release.
- **Counterparty Information**: Client / Freelancer name, verified identity status, and business billing details.
- **Financial Breakdown**:
  - Gross Amount (GigCoin / VND equivalent)
  - Platform Service Fee (Client fee / Freelancer commission)
  - Tax & Processing Charges
  - Net Payout / Net Paid Amount
- **Status Indicator**: `Paid`, `Pending Processing`, `Refunded`, or `Failed`.

---

## 3. Printable Receipts & PDF Export

- **Print View**: Formatted CSS layout suitable for browser printing (`Ctrl + P`).
- **PDF Download**: One-click export generating an official PDF document containing security verification hashes.
- **Tax Compliance**: Suitable for corporate expense reporting and financial audits.
