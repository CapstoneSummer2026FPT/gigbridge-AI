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

## 2. Current Button Behavior

The page shows a short processing state and then navigates back. It does not call the wallet API, create a provider checkout, or credit GigCoin. Although the screen displays a “Secure payment powered by Stripe” note, the current component contains no Stripe integration. These package values should therefore not be presented as completed purchases or authoritative exchange pricing.

---

## 3. Displayed Benefits

The marketing list mentions priority applications, improved visibility, exclusive opportunities, and profile boosts. Access to concrete Premium or promotion functions remains controlled by their own backend entitlement and wallet rules; selecting a package here does not unlock them.

---

## 4. Real Top-Up Route

Users who need spendable GigCoin should use `/wallet/deposit`. That page creates a PayOS order, accepts an allowed VND amount, converts it at the displayed wallet rate, synchronizes the provider status after return, and updates the ledger. Wallet History should be used to confirm final settlement. This distinction keeps an unfinished public-facing package prototype from being mistaken for a financial operation.
