---
title: "GigBridge Wallet Withdrawals"
source: "https://gigbridge.id.vn/wallet/withdrawals"
description: "Bank withdrawal requests for eligible earned GigCoin."
---

# Wallet Withdrawals

**Route:** `/wallet/withdrawals`

**Access:** Signed-in users with completed setup; payout actions are intended for accounts with eligible earnings.

The page separates deposited, withdrawable, held, and pending-withdrawal GigCoin. Only GigCoin marked as earned and withdrawable can be paid out; deposited GigCoin is for in-app spending and cannot be withdrawn.

To create a request, the user enters an amount within the current backend limits, selects a saved bank account, reviews the conversion, processing fee, and net VND amount, then confirms. The GigCoin is locked in Pending Withdrawal until PayOS returns a terminal result.

Withdrawal history shows provider/order details, masked bank information, timestamps, status, failures, and a sync action for non-terminal requests.
