---
title: "GigBridge Freelancer Dashboard"
source: "https://gigbridge.id.vn/freelancer/dashboard"
description: "Freelancer overview of profile strength, job opportunities, proposals, contracts, earnings, and active work."
---

# Freelancer Dashboard

The Freelancer Dashboard summarizes the account's readiness, opportunity pipeline, work activity, and wallet performance. It provides shortcuts into jobs, profile editing, Premium tools, notifications, and active project workspaces.

---

## 1. Page Access & Main Navigation

- **Route**: `/freelancer/dashboard`
- **Access**: Freelancers with completed profile setup.
- **Browse Jobs**: Opens `/jobs/browse` to search the full job catalog.
- **Edit Profile**: Uses the profile edit route, which redirects to Settings.
- **Notifications**: Opens the full notification inbox.

---

## 2. Profile Readiness

- **Profile Completion**: Shows the calculated completion percentage and encourages the user to add missing information.
- **Profile Facts**: Summarizes information such as review rating and active professional title.
- **Profile Action**: Opens Settings so the Freelancer can update basic details, taxonomy, biography, portfolio, and work experience.

The dashboard reflects saved profile data. Editing is completed in Settings rather than directly inside the dashboard cards.

---

## 3. Work & Proposal Statistics

- **Available Balance**: Current wallet balance displayed in GigCoin.
- **Completed Projects**: Count of completed engagements.
- **Pending Proposals**: Proposals still awaiting a final outcome.
- **Active Contracts**: Current contracts connected to ongoing work.
- **Earnings Chart**: Displays earnings history when financial time-series data is available.

These values are summaries and do not replace Wallet History, Proposals, or Contracts as the detailed source of activity.

---

## 4. Jobs & Active Work

- **Recent Open Jobs**: Displays loaded job opportunities and links each card to `/jobs/:id`.
- **View All Jobs**: Opens Browse Jobs for search and filtering.
- **Active Work**: Lists ongoing projects with status and a button to open `/workspace/:contractId`.
- **Empty States**: Explain when no suitable jobs or active projects are currently available.

Recent jobs are opportunities, not guaranteed personal matches or offers. The Freelancer must review the job and complete the appropriate application flow.

---

## 5. Premium Panel

The collapsible Premium area displays the account's Premium state and links to:

- **Points**: `/premium/freelancer/points`
- **Rank Protection**: `/premium/freelancer/rank-protection`
- **Promotions**: `/premium/freelancer/promotions`
- **Premium Dashboard**: `/premium/freelancer`

Availability and balances shown in these tools come from the subscription service; opening the panel does not purchase or activate a benefit.

---

## 6. Loading & Interpretation

- A dash or empty chart can indicate that data is loading or that no financial activity exists yet.
- Dashboard counts can change after proposal, contract, milestone, review, or wallet actions complete.
- The page does not automatically submit proposals, sign contracts, or withdraw earnings.
