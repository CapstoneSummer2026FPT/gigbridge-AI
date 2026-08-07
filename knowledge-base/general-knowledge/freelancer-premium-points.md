---
title: "GigBridge Freelancer Premium Elo Points"
source: "https://gigbridge.id.vn/premium/freelancer/points"
description: "Freelancer Elo tier progress and recent point activity."
---

# Freelancer Premium Elo Points

The Points tab explains a Premium freelancer's current Elo position and the activity that changed it. It uses the server's tier calculation rather than estimating rank from profile completeness or review averages in the browser.

---

## 1. Access & Route

- **Route**: `/premium/freelancer/points`
- **Entitlement**: Active Freelancer Premium is required; otherwise the shared hub redirects to pricing.
- **Loaded resource**: Current Elo points, tier name, tier progress percentage, next tier name/threshold, and recent point transactions.

This route opens the same Premium hub with the Points tab selected, so renewal and navigation behavior remain consistent with `/premium/freelancer`.

---

## 2. Tier Progress

The heading pairs the tier name with the current Elo value. A progress bar uses the backend `tierProgress` value, capped visually at 100%. If another tier exists, the page calculates how many points remain from `nextTierThreshold - eloPoints`. At the highest configured tier, it replaces that calculation with a highest-tier message.

---

## 3. Recent Activity

Each point transaction shows its source or activity reason, localized timestamp, and signed delta. Positive changes are green with a plus prefix; negative changes are red. A legacy integrity-adjustment reason receives a dedicated label so administrative migration/correction activity is not presented as ordinary marketplace work.

If no transactions exist, the page says there is no recent point activity rather than implying the account has no Elo.

---

## 4. Interpretation

Elo points and Premium subscription coverage are related features but separate records. Purchasing or extending Premium unlocks the tier interface; it does not promise a point increase. Likewise, displayed progress does not itself activate promotion or rank protection. Those actions are performed from their own tabs and remain subject to backend policy.
