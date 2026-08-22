---
title: "GigBridge Elo Rating History"
source: "https://gigbridge.id.vn/elo"
description: "User and Freelancer ELO score history tracking rank status, tier levels, rating adjustments, penalty logs, and appeal options."
---

# Elo Rating History

The Elo Rating History page provides a comprehensive record of a Freelancer or user's performance score on the platform. ELO scores reflect job completion success, milestone delivery timeliness, client reviews, and compliance records.

---

## 1. Page Access & Navigation

- **Route**: `/elo`
- **Access**: Authenticated Freelancers and Clients.
- **Header Summary**: Displays current numerical Elo score (e.g., 1450), rank tier status (Bronze, Silver, Gold, Platinum, Diamond), and active rank protection (vacation mode) status.

---

## 2. Elo Score Overview & Breakdown

- **Current Rating**: Real-time calculated score based on historic contract completion metrics.
- **Rank Tier Badge**: Visual indicator of current platform status and benefits eligibility.
- **Score Components**:
  - **Contract Completion Rate**: Impact of successfully closed contracts versus canceled or disputed contracts.
  - **Client Review Ratings**: Weighted score derived from client feedback ratings.
  - **On-Time Milestone Delivery**: Bonus for meeting milestone deadlines without extension requests.
  - **Dispute Outcomes**: Score deductions for adverse dispute rulings or policy violations.

---

## 3. Rating Audit Log

Chronological table detailing every score adjustment:
- **Timestamp**: Date and time of the score update.
- **Event Type**: Contract Completed, Positive Review, Dispute Penalty, Inactivity Decay, or Administrative Adjustment.
- **Score Delta**: Positive (`+15`) or negative (`-30`) point change.
- **Reference**: Clickable link to the associated Contract ID or Dispute ID.
- **Notes**: Reason summary provided by the automated system or Admin auditor.

---

## 4. Rank Protection & Appeals

- **Rank Protection**: Indicates if rank freeze (vacation protection) was active during inactive periods to prevent rank decay.
- **Penalty Appeals**: If an Elo penalty was assigned due to a disputed project, users can click **Appeal Penalty** to open an appeal request reviewed by Administrators at `/admin/elo/appeals`.
