---
title: "GigBridge Wallet Withdrawals"
source: "https://gigbridge.id.vn/wallet/withdrawals"
description: "Bank withdrawal requests for eligible earned GigCoin."
---

# Wallet Withdrawals

Wallet Withdrawals lets freelancers transfer eligible earned GigCoin to an active bank account. It deliberately excludes deposited GigCoin and keeps requested funds locked until the payout provider reaches a final status.

---

## 1. Wallet Pools

- **Route**: `/wallet/withdrawals` (`/wallet/early-payout` redirects here).
- **Deposited**: Spendable in GigBridge, but not withdrawable.
- **Earned/withdrawable**: Contract earnings currently eligible for bank payout.
- **Escrow held**: Still protected inside contracts.
- **Pending withdrawal**: Locked while a payout request is processed.

The page loads the wallet, latest 50 withdrawals, server-provided withdrawal settings, and saved bank accounts.

---

## 2. Amount & Bank Validation

Quick amounts are 10, 50, 100, 500, 1,000, and 5,000 GigCoin. The actual minimum, per-request maximum, daily maximum, fixed VND fee, and VND-per-token rate come from current backend settings. The usable maximum is the smallest of the configured maxima and the earned balance. Net VND after the fixed fee must be positive.

Only active accounts with a supported bank BIN can be selected. The default active account is preferred; disabled accounts remain visible for repair but cannot receive a withdrawal. Bank account values are masked in the interface.

---

## 3. Request & Processing

Before submission, the summary shows GigCoin requested, gross VND conversion, processing fee, and net amount. The API request includes the selected bank account and an idempotency key tied to the amount/account draft, preventing repeated clicks from intentionally creating duplicate payouts.

Funds enter `Pending`, `Processing`, or `Sync Required` before reaching `Success`, `Failed`, or `Cancelled`. Non-final records expose `Check status`; final records show completion time or failure reason. GigBridge automatically creates the payout and can retry provider synchronization when PayOS is temporarily unavailable.

---

## 4. Availability

When withdrawals are disabled for maintenance, the form is locked. A request can also be blocked by insufficient earned balance, limits, fee math, or invalid bank configuration. Depositing more GigCoin does not increase the withdrawable pool.
