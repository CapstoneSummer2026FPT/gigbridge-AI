---
title: "GigBridge Financial Overview"
source: "https://gigbridge.id.vn/financial-overview"
description: "Role-aware GigCoin payments or earnings analytics and CSV export."
---

# Financial Overview

Financial Overview summarizes contract-related GigCoin movement for the signed-in user's role. Clients see spending/payment language, while freelancers see earnings/received language; both views use the same backend-defined period and transaction categories.

---

## 1. Period & Role

- **Route**: `/financial-overview`
- **Periods**: Day, month, and year; month is initially selected.
- **Currency**: Values are presented in GigCoin.
- **Role adjustment**: `Released` is labelled paid for a client and received for a freelancer.

Changing the period reloads the overview. A failed request displays retry controls rather than charts built from missing values.

---

## 2. Totals & Progress

The dashboard reports total contract value, progress amount (paid or received), escrow-funded value where relevant, service fees, refunds, and comparison/trend data returned for the selected period. A progress visualization separates completed value from remaining contract value and caps progress at the total.

Transaction categories include escrow, released, refund, and service fee. The client chart includes escrow-funded amounts alongside paid amounts and fees; the freelancer view emphasizes received amounts and fees.

---

## 3. Charts & Recent Activity

Period buckets are shown in bar and progress charts, followed by a transaction table containing date, project, category/status, and amount. Category labels reflect financial meaning rather than generic wallet success: money in escrow is not yet the same as paid/received, and a refund is not ordinary income.

The empty state requires both zero summary values and no transactions. This prevents a sparse chart from hiding a meaningful total.

---

## 4. CSV Export

Export generates a UTF-8 CSV in the browser. It includes report metadata, summary rows, period breakdown, and the transaction table with localized labels. The export mirrors the currently loaded role and period; it is an analytical report, not a bank statement or substitute for the Wallet History ledger.
