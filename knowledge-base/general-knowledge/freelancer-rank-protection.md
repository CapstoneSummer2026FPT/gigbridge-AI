---
title: "GigBridge Freelancer Vacation Mode"
source: "https://gigbridge.id.vn/premium/freelancer/rank-protection"
description: "Premium rank protection settings for a freelancer's planned absence."
---

# Freelancer Vacation Mode and Rank Protection

Vacation Mode lets an active Premium freelancer protect rank during a planned absence. It is an explicit, dated setting: Premium access alone does not automatically enable protection.

---

## 1. Access & Current State

- **Route**: `/premium/freelancer/rank-protection`
- **Entitlement**: Active Freelancer Premium.
- **Inactive view**: Shows a date field, optional reason, and activation action.
- **Active view**: Shows the protected-until date and an `End Vacation` action.

This route opens the Vacation tab in the same Premium hub and shares its loading, error, and entitlement behavior.

---

## 2. Date Rules

The selected end date cannot be earlier than today and cannot extend beyond the current Premium subscription end date. The activation button requires both entitlement and a selected date. When sent to the backend, the chosen day is converted to an ISO timestamp ending at 23:59:59 for that date. The reason is optional.

---

## 3. Confirmation & Changes

Activating or cancelling protection opens a confirmation modal. Controls are disabled while the request is pending. After a successful response, protection, current promotion, and wallet-related resources are refreshed and the server message is shown. A failure leaves the existing state intact and displays the returned error.

---

## 4. Scope of Protection

The page describes temporary Elo/rank protection; it does not cancel contracts, pause milestone deadlines, hide existing responsibilities, or guarantee marketplace placement. Freelancers should still coordinate active project absences with clients in the workspace. Ending vacation removes the protection setting immediately through its own backend action, while cancelling Premium auto-renewal only affects future subscription coverage.
