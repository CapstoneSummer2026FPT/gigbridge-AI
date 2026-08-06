---
title: "GigBridge Wallet History"
source: "https://gigbridge.id.vn/wallet/history"
description: "Searchable wallet ledger and cumulative transaction summary."
---

# Wallet History

Wallet History is the user-facing GigCoin ledger. It combines lifetime summary totals with the most recent transaction records, then lets the user search, filter, and inspect the metadata behind a balance change.

---

## 1. Loading & Reconciliation

- **Route**: `/wallet/history`
- **List size**: The page loads up to 100 recent transactions.
- **Summary**: Lifetime totals are requested separately so stat cards are not limited to those 100 rows.
- **PayOS reconciliation**: Pending top-ups that contain a gateway order code are synchronized automatically; the page silently reloads the list and summary when statuses change.

---

## 2. Summary Cards

The cards show total successful deposits, total escrow holds, total refunds, total withdrawn, and the number of pending transactions. Only successful transactions contribute to monetary fallback totals. This avoids counting a pending or cancelled provider request as settled money.

---

## 3. Search & Filters

Users can search transaction descriptions and identifiers, filter by wallet transaction type, and filter by `Pending`, `Success`, `Failed`, or `Cancelled` status. Types include administrative adjustments, top-ups, holds, releases/contract payments, refunds, withdrawals, subscription purchases, and promotion purchases as represented by the ledger. Positive and negative signs reflect whether the entry credits or debits the wallet.

---

## 4. Transaction Details

Each row shows description, type badge, status, timestamp, GigCoin amount, and linked contract identifier when present. Opening a record provides its full IDs and provider/contract context. An empty filtered result is distinct from a failure to load data.

The history is the safest place to verify whether a top-up, refund, release, Premium purchase, promotion, or withdrawal actually settled. A success message on an initiating page should not be used as a substitute for its final ledger status.
