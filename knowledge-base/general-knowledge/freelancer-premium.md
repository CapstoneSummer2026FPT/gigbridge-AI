---
title: "GigBridge Freelancer Premium Hub"
source: "https://gigbridge.id.vn/premium/freelancer"
description: "Overview of an active Freelancer Premium subscription and its benefits."
---

# Freelancer Premium Hub

The Freelancer Premium Hub is the management area for an active freelancer subscription. It combines plan coverage, Elo progress, vacation/rank protection, profile promotions, renewal, and Premium-related transaction history under tabbed navigation.

---

## 1. Access & Entitlement

- **Route**: `/premium/freelancer`
- **Tabs**: Overview, Points, Vacation, Promotions, and History.
- **Active condition**: The current subscription identifies the user as Premium and its end date is in the future.
- **No active plan**: Redirects to `/premium/freelancer/pricing` after entitlement loading finishes.

The Overview shows plan name, remaining covered time, current Elo/tier progress, vacation status, and active promotion status.

---

## 2. Subscription Controls

The freelancer can top up/extend the plan from Pricing and toggle automatic renewal. When auto-renewal is enabled, the help text explains that GigCoin will be used; when disabled, access ends at the current end date unless manually renewed. Current and subscription-history resources refresh after a successful change.

---

## 3. Premium Tools

- **Points** shows the current Elo tier, progress toward the next tier, and recent point changes.
- **Vacation** activates or ends rank protection within the subscription period.
- **Promotions** builds and purchases a profile card, manages its boost/queue position, and shows campaign history.
- **History** combines subscription coverage with relevant wallet debits.

These tools are separate operations: subscription access does not automatically spend promotion coins or enable vacation mode.

---

## 4. Refresh & Errors

Plan, points, protection, promotion, transaction, and history data come from separate resources. Loading placeholders avoid displaying zeroes as settled state. Mutations use confirmation, disable duplicate clicks, and show backend success or error messages before refreshing the affected resources.
