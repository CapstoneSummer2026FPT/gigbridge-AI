---
title: "GigBridge Freelancer Profile Promotions"
source: "https://gigbridge.id.vn/premium/freelancer/promotions"
description: "Premium profile-promotion package selection, preview, and campaign management."
---

# Freelancer Profile Promotions

Profile Promotions lets an entitled freelancer design a sponsored card, purchase a campaign with optional GigCoin boost, and track its live queue position and performance. The page is a campaign manager, not just a static benefit description.

---

## 1. Campaign Builder

- **Route**: `/premium/freelancer/promotions`
- **Entitlement**: Active Freelancer Premium is required to activate or boost.
- **Required card data**: Uploaded photo URL and display name.
- **Optional display**: Quote can be enabled and edited; job title can be shown and is supplied from the promotion draft.
- **Images**: JPEG, PNG, and WebP are accepted; maximum bytes come from the server promotion policy.

Display-name, quote, and job-title character limits also come from that policy.

---

## 2. Target & Purchase

The draft provides a base click target and target-clicks-per-coin rate. Entering a desired target calculates the necessary whole GigCoin boost; entering an initial boost projects its click target. Activation requires valid integer boost, available wallet tokens, policy limits, Premium entitlement, photo, and display name. The purchase uses an idempotency key.

---

## 3. Active Campaign Manager

The active view shows end time, clicks versus target, impressions, boost weight, tokens spent, and queue position. It refreshes every 15 seconds. A boost must be an integer inside the server minimum/maximum and available balance. Before purchase, a ladder projects the new boost weight and queue position among up to eight nearby rows.

The user can also end a campaign early after browser confirmation.

---

## 4. Preview & History

A live card preview reflects the chosen photo, name, quote, and job title. The history combines active, queued, and past campaigns with date ranges and `Ongoing`, `Queued`, or `Ended` labels. Queue placement is comparative and can change as other campaigns change; buying a target improves weighted placement but does not guarantee a fixed number of impressions or hires.
