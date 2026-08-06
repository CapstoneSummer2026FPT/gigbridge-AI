---
title: "GigBridge Wallet Deposit"
source: "https://gigbridge.id.vn/wallet/deposit"
description: "PayOS top-up flow for converting VND into spendable GigCoin."
---

# Wallet Deposit

**Route:** `/wallet/deposit`

**Access:** Signed-in users with completed setup.

Users choose a preset VND amount or enter a custom amount. The page shows the corresponding GigCoin using the displayed rate of **1 GigCoin = 1,000 VND**. The current implementation accepts amounts from **10,000 VND to 250,000,000 VND**.

Continuing creates an idempotent PayOS top-up and redirects to the provider's checkout page. After PayOS returns, GigBridge synchronizes the order status, refreshes the wallet, and offers a link to Wallet History. A cancelled or still-pending payment does not count as a successful wallet credit.

Deposited GigCoin is spendable in the application; withdrawal eligibility is tracked separately from earned GigCoin.
