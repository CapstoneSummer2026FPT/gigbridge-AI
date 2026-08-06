---
title: "GigBridge Freelancer Premium Pricing"
source: "https://gigbridge.id.vn/premium/freelancer/pricing"
description: "Freelancer Premium plans and GigCoin purchase confirmation."
---

# Freelancer Premium Pricing

Freelancer Premium Pricing compares the free freelancer tools with paid plans returned by the Premium API. The page uses GigCoin wallet balance for purchase and does not assume that opening a plan card grants Premium access.

---

## 1. Plans & Billing Period

- **Route**: `/premium/freelancer/pricing`
- **Filters**: Monthly and yearly.
- **Free plan**: Job browsing/applications and a standard freelancer profile.
- **Paid plans**: Show the backend plan name, GigCoin price, description, duration, and parsed feature list.

When a yearly plan is not separately returned but a monthly configuration exists, the frontend derives a yearly presentation at ten times the monthly price and describes it as two months free. Published backend plans remain the primary source.

---

## 2. Feature Context

The pricing header highlights Elo tiers, rank protection, Premium identity, and profile promotion. These features have their own eligibility rules and management screens. Buying Premium establishes the subscription entitlement; it does not automatically activate vacation mode or purchase a promotion campaign.

---

## 3. Purchase Confirmation

Choosing a plan opens a modal with its GigCoin price, current total spendable balance, and calculated remaining balance. Insufficient balance replaces confirmation with `Get GigCoin`, linking to `/wallet/deposit`. An affordable purchase sends the plan ID with a generated idempotency key and disables repeated clicks while processing.

---

## 4. Result & Renewal

On success, the user is redirected to `/premium/freelancer` with an activation notice. On failure, the backend message remains visible and no entitlement is inferred. Subscription purchases appear in Premium history and Wallet History. Extension and auto-renewal are managed from the Premium hub, where the current expiration and combined coverage can be verified.
