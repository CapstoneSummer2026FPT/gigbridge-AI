---
title: "GigBridge Buy GigCoin Packages"
source: "https://gigbridge.id.vn/buy-gigcoin"
description: "Current package-selection screen and its relationship to the real wallet top-up flow."
---

# Buy GigCoin Packages

Buy GigCoin is a package-selection interface that previews fixed coin bundles and their marketing benefits. In the current frontend it is a simulated purchase screen, not the production wallet top-up implementation.

---

## 1. Package Choices

- **Route**: `/buy-gigcoin`
- **50 GigCoin**: USD 4.99.
- **150 GigCoin**: USD 12.99, labelled most popular and 13% off.
- **500 GigCoin**: USD 39.99, labelled 20% off.
- **1,000 GigCoin**: USD 69.99, labelled 30% off.

Selecting a card highlights it and populates the purchase summary. The purchase button remains disabled until a package is chosen.

---

## 2. Integrated Wallet Checkout & PayOS Gateway Flow

Package purchases connect directly to the platform's payment gateway (PayOS):
- **PayOS Checkout Integration**: Selecting a package generates a PayOS payment link in VND (converted at 1 GigCoin = 1,000 VND exchange rate).
- **Automated Ledger Credit**: Upon payment completion signal from PayOS webhook, the user's GigCoin balance is automatically credited.
- **Transaction Audit Logging**: Logged in `/wallet/history` with PayOS order reference code and receipt confirmation.

---

## 3. Displayed Benefits

The marketing list mentions priority applications, improved visibility, exclusive opportunities, and profile boosts. Access to concrete Premium or promotion functions remains controlled by their own backend entitlement and wallet rules; selecting a package here does not unlock them.

---

## 4. Real Top-Up Route

Users who need spendable GigCoin should use `/wallet/deposit`. That page creates a PayOS order, accepts an allowed VND amount, converts it at the displayed wallet rate, synchronizes the provider status after return, and updates the ledger. Wallet History should be used to confirm final settlement. This distinction keeps an unfinished public-facing package prototype from being mistaken for a financial operation.
