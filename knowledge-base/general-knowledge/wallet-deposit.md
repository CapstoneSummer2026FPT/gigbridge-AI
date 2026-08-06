---
title: "GigBridge Wallet Deposit"
source: "https://gigbridge.id.vn/wallet/deposit"
description: "PayOS top-up flow for converting VND into spendable GigCoin."
---

# Wallet Deposit

Wallet Deposit is the implemented top-up flow for adding spendable GigCoin through a PayOS checkout. It shows the user's current spendable balance, converts the selected VND amount at the displayed platform rate, and synchronizes the provider result after return.

---

## 1. Amount Selection

- **Route**: `/wallet/deposit`
- **Conversion used by the page**: 1 GigCoin per 1,000 VND.
- **Allowed VND range**: 10,000–250,000,000 VND.
- **Quick amounts**: 50,000; 100,000; 200,000; 500,000; 1,000,000; and 2,000,000 VND.
- **Custom amount**: Replaces the selected quick amount and must remain inside the same limits.

The interface calculates the resulting GigCoin before checkout. An invalid amount or an in-progress request disables submission.

---

## 2. PayOS Checkout

GigBridge creates a top-up using the token amount, success/cancel return URLs, and a generated idempotency key. When PayOS returns a checkout URL, the browser is redirected there. The gateway order code is temporarily retained locally so return synchronization can continue even if it is not present in every callback parameter.

---

## 3. Return & Synchronization

On a success return, the page does not immediately assume the balance is final. It attempts to synchronize the PayOS order up to five times, with a three-second interval between non-final attempts. It then reloads the wallet and broadcasts a wallet-updated event. If provider confirmation remains pending, a warning tells the user to check again rather than claiming credit.

A cancel return removes the saved order code and requests a status sync when possible. Users can reload their balance or open Wallet History.

---

## 4. Balance Meaning

Deposited GigCoin is spendable for platform purchases and contract actions supported by the wallet, but it is not earned/withdrawable GigCoin. The withdrawal page keeps deposited, earned, escrow-held, and pending-withdrawal pools distinct.
