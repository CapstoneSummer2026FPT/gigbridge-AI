---
title: "GigBridge Wallet & Payments (vnpay, gigcoin, gcoin)"
source: "Financial Subsystem Architecture"
description: "Documentation on deposit channels (vnpay, bank transfer, chuyen khoan), GigCoin (gigcoin, gcoin, g-coin), bank transfer validation, payout withdrawals, and subscription packages."
keywords: "vnpay, gigcoin, gcoin, g-coin, bank transfer, chuyen khoan, deposit, withdrawal, wallet"
---

# Wallet & Financial Operations (vnpay, gigcoin, gcoin)

GigBridge integrates a multi-currency wallet subsystem allowing users to deposit funds (via vnpay, mock card checkout, or bank transfer), purchase platform G-coins (gigcoin, gcoin, g-coin), pay for contracts, and withdraw earnings.

---

## 1. Currencies & Tokens

- **VND (Vietnamese Dong)**: The primary fiat currency used for account balances, subscription fees, deposits, and bank withdrawals.
- **GIG (GigCoin)**: The platform token used for freelancer premium features, bidding boost packages, and specific contract payments. Users can purchase G-coins using their VND wallet balance.

---

## 2. Deposits & Payment Proof Validation

Users can fund their wallets via the **Deposit** page.

- **Payment Methods**: Supports mock card checkouts and local bank transfers.
- **Bank Transfer Proof Flow**:
  1. The client copies the platform bank account details and transaction code from the Deposit screen.
  2. The client transfers funds using their banking application.
  3. The client uploads a screenshot of the transaction receipt (payment proof) on the Upload Payment Proof screen.
  4. Platform administrators audit the uploaded screenshot and transaction code. Upon validation, the funds are credited to the user's wallet balance.

---

## 3. Withdrawals & Payout Limits

Freelancers can request payouts of their earnings via the **Withdrawals** page.

- **Minimum Withdrawal Limit**: The minimum payout amount is **50,000 VND**.
- **Audit Approval**: Withdrawal requests enter a "Pending" queue. Platform administrators audit user profiles, transaction logs, and contract activity before authorizing manual bank transfers.

---

## 4. Subscription Plans & Limits

GigBridge offers tier-based subscriptions to unlock advanced features:

### Freelancer Subscription Packages

| Feature / Limit       | Freelancer Basic | Freelancer Premium Monthly      | Freelancer Premium Yearly       |
| :-------------------- | :--------------- | :------------------------------ | :------------------------------ |
| **Price**             | Free             | 150 GIG / month                 | 1500 GIG / year (saves 300 GIG) |
| **Monthly Proposals** | Max 10 bids      | Unlimited                       | Unlimited                       |
| **Identity Badge**    | Standard         | Premium Identity Badge          | Premium Identity Badge          |
| **Rank Protection**   | No               | Elo Tiers & Vacation Protection | Elo Tiers & Vacation Protection |
| **Profile Promotion** | No               | Accessible                      | Accessible                      |

### Client Subscription Packages

| Feature / Limit       | Client Basic                      | Client Premium                             |
| :-------------------- | :-------------------------------- | :----------------------------------------- |
| **Price**             | Free                              | 500,000 VND / month                        |
| **Monthly Job Posts** | Max 3 listings                    | Unlimited                                  |
| **AI Matching**       | Standard matching recommendations | Advanced AI candidate matching & filtering |
| **Priority Support**  | Standard Email Support            | 24/7 Priority Support                      |
| **AI Pre-Screening**  | Standard                          | Direct AI Interview Integration            |
