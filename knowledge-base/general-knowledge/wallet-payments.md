---
title: "GigBridge Wallet and Payments"
source: "Current wallet, Premium, and escrow implementation"
description: "GigCoin balances, top-ups, escrow holds, service fees, withdrawals, and Premium purchases."
---

# Wallet and Payments

## GigCoin and VND

GigBridge displays contract and in-app payment amounts in GigCoin. Wallet Deposit currently shows the conversion **1 GigCoin = 1,000 VND** and creates VND checkouts through PayOS.

## Balance types

The wallet distinguishes deposited GigCoin, earned/withdrawable GigCoin, held GigCoin, pending withdrawals, and total spendable balance. Deposited GigCoin can be spent inside GigBridge but cannot be withdrawn. Only eligible earned GigCoin is withdrawable.

## Top-ups and transaction status

Wallet Deposit redirects to PayOS and synchronizes the returned order. A checkout return is not final proof of payment until GigBridge records a successful status. Wallet History shows deposits, holds, refunds, withdrawals, service fees, and other supported transaction types.

## Escrow and fees

Contract funding moves eligible spendable GigCoin into escrow/hold state. Supported workflow actions use the current **1% service-fee rate**, with charges recorded separately. The user must have enough eligible balance for both the action and any required fee.

## Withdrawals

The withdrawal page uses backend-provided limits/settings and a saved bank account. It shows the processing fee and net VND before confirmation. Requested GigCoin remains locked as Pending Withdrawal until the payout provider reaches a final status.

## Premium and promotions

Published Premium plans and promotion packages are purchased with spendable GigCoin. Prices, durations, and features are loaded from the backend and should not be treated as fixed unless displayed by the current pricing page.
