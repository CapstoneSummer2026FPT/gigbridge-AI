---
title: "GigBridge Admin Bank Withdrawals"
source: "https://gigbridge.id.vn/admin/withdrawals"
description: "Administrator financial portal for reviewing user bank withdrawal requests, verifying account details, approving payouts, and managing payout receipts."
---

# Admin Bank Withdrawals

The Admin Bank Withdrawals page allows administrators and financial staff to review, audit, approve, or reject bank withdrawal requests submitted by platform users.

---

## 1. Page Access & Filters

- **Route**: `/admin/withdrawals`
- **Access**: Restricted to `Admin` role.
- **Status Filters**: `Pending Verification`, `Processing`, `Completed`, `Rejected`.

---

## 2. Withdrawal Request Details

For each withdrawal entry:
- **User Account**: Name, User ID, Profile link, and current GigCoin wallet balance.
- **Withdrawal Amount**: Gross withdrawal value requested in VND and equivalent GigCoins deducted.
- **Bank Account Information**: Bank name, account number, account holder name, and swift code.
- **Early Payout Flag**: Indicates if the request is an early payout with applicable service fee deductions.
- **Timestamp & Transaction ID**: Unique payout reference code.

---

## 3. Approval & Processing Workflow

- **Verify Account Match**: Audit check to ensure bank account holder name matches verified user KYC identity.
- **Approve Payout**: Triggers bank transfer batch processing and marks transaction as `Completed`.
- **Upload Payout Receipt**: Attach transaction confirmation slip or bank reference ID.
- **Reject Request**: Reject request with reason (e.g., mismatched bank details, invalid account number). Deducted GigCoins are automatically refunded to the user's wallet.
