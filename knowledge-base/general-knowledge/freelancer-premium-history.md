---
title: "GigBridge Freelancer Premium History"
source: "https://gigbridge.id.vn/premium/freelancer/history"
description: "Subscription coverage and Premium-related wallet activity for freelancers."
---

# Freelancer Premium History

The History tab places Premium subscription periods beside wallet debits for subscriptions and promotions. It helps freelancers distinguish entitlement coverage from the GigCoin transactions used to buy Premium services.

---

## 1. Access & Route

- **Route**: `/premium/freelancer/history`
- **Entitlement**: The shared Freelancer Premium hub requires an active, unexpired plan.
- **Data sources**: Subscription history and wallet transaction history are loaded separately.

This means one side can temporarily fail or be empty without the page fabricating matching entries on the other side.

---

## 2. Subscription History

Each subscription row displays the plan name, start date, end date, and status label from `PremiumSubscriptionStatus`. The time-remaining component on the Overview can use multiple history records to represent available coverage, while this tab preserves the individual periods.

An empty list produces a no-subscription-history message. It does not remove the current entitlement until the current-subscription resource confirms there is no active coverage.

---

## 3. Wallet Activity

The wallet column filters for `Promotion Purchase` and `Subscription Purchase` transaction types. Each entry shows its type, localized timestamp, and a negative GigCoin amount, reflecting the debit. Other wallet events—deposits, contract holds/releases, refunds, and withdrawals—belong in the full Wallet History page and are intentionally not mixed into this Premium-specific list.

---

## 4. Interpreting the Records

A subscription row states when benefits apply; a wallet row states that tokens moved. They may not have identical counts because extensions, administrative actions, failure states, or separate promotions have different lifecycles. For final settlement status and transaction identifiers, use `/wallet/history`. For current renewal behavior and expiration, use the Overview. For active/queued/ended campaign details, use Promotions.
