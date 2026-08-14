---
title: "GigBridge Admin Dashboard"
source: "https://gigbridge.id.vn/admin"
description: "Executive control panel for Administrators displaying system-wide analytics, financial escrow volume, active user counts, and health alerts."
---

# Admin Dashboard

The Admin Dashboard provides high-level executive visibility into system performance, financial transactions, user activity, platform commission earnings, and operational alerts.

---

## 1. Page Access & Authorization

- **Route**: `/admin`
- **Access**: Strictly restricted to users with `Admin` role privileges (`AdminRoute`).

---

## 2. Key Metric Widgets

- **Total Platform Users**: Total count of registered accounts breakdown by Clients and Freelancers.
- **Active Job Postings**: Volume of open, filled, and archived job listings.
- **Escrow Volume**: Total financial value currently locked in contract escrow across all active milestones.
- **Platform Commissions Revenue**: Accumulated system fees collected from completed contract payouts and premium subscriptions.
- **Pending Disputes**: Number of open dispute cases requiring administrator arbitration.
- **Pending Bank Withdrawals**: Count and total amount of bank withdrawal requests awaiting verification.

---

## 3. Quick Navigation & Management Short-cuts

- **User Moderation Portal**: Shortcut to `/admin/users`.
- **Contract & E-Sign Audit**: Link to `/admin/contracts`.
- **Dispute Resolution Hub**: Quick jump to `/admin/disputes`.
- **Financial & Withdrawal Audit**: Link to `/admin/withdrawals`.
- **System Tracking & Health**: Shortcut to `/admin/system-tracking`.

---

## 4. Real-time System Alerts & Warnings

- Flags system anomalies such as failed API integrations (Gladia STT, ElevenLabs TTS), elevated error rates, suspicious IP activity, or unhandled dispute timeouts.
