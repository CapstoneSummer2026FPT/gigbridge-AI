---
title: "GigBridge Client Premium Pricing"
source: "https://gigbridge.id.vn/premium/client/pricing"
description: "Monthly/yearly Client Premium plans and GigCoin purchase flow."
---

# Client Premium Pricing

Client Premium Pricing compares the free client experience with currently published Premium plans. Names, prices, duration, and feature lists come from the Premium API, so this page should not be documented with a fixed price when administrators can change plan configuration.

---

## 1. Plan Selection

- **Route**: `/premium/client/pricing`
- **Billing filters**: Monthly and yearly.
- **Free card**: Core job posting, proposal review, contract management, hiring, and manual freelancer discovery.
- **Premium cards**: Render only plans published for the chosen period, including their backend description and parsed feature list.

If no option exists for a period, the page explicitly says that an administrator has not published one. A current Premium client sees `Extend`; a Standard client sees `Choose`.

---

## 2. Wallet Confirmation

Selecting a paid plan opens a confirmation modal showing:

- Plan name and GigCoin price.
- Current total spendable GigCoin.
- Expected balance after purchase when affordable.

If the balance is insufficient, confirmation is replaced by `Get GigCoin`, which routes to Wallet Deposit. The purchase request uses the plan ID and a generated idempotency key.

---

## 3. Purchase Result

The button is locked while processing. API errors remain in the pricing page and do not activate features. A successful response redirects to `/premium/client` with a purchased state so the hub can refresh and display activation. Wallet History records the corresponding subscription debit.

---

## 4. Entitlement Principle

Premium availability depends on an active, unexpired subscription returned by the backend—not merely selecting a plan or visiting the hub. Monthly/yearly labels and displayed value are informational until the GigCoin transaction succeeds. Renewal and cancellation are managed from the Client Premium Hub.
