---
title: "GigBridge Talent Matching"
source: "https://gigbridge.id.vn/talent-matching"
description: "Client talent directory with saved Freelancers, invitations, and Premium job-specific Smart Matching."
---

# Talent Matching

Talent Matching combines a general Freelancer directory with the Client's saved shortlist and a Premium recommendation engine. Directory browsing remains available to standard Clients; Smart Matching adds a ranked, job-specific view.

---

## 1. Page Access & Modes

- **Route**: `/talent-matching`
- **Access**: Clients with completed profile setup.
- **Browse Freelancers**: Full loaded directory.
- **Saved Freelancers**: Only profiles saved by the Client.
- **Smart Matching**: Client Premium mode requiring a selected Open job.
- **URL State**: `tab=browse`, `tab=saved`, or `tab=smart`; `job=:id` can preselect an open job.

---

## 2. Browse & Saved Directory

Search matches name, professional title, skill, location, and category. Category filtering can be combined with the keyword.

Directory cards show available identity, title, location, categories, skills, and profile information. Clients can:

- Open `/profile/freelancer/:id`.
- Save or unsave the Freelancer.
- Invite the Freelancer to an eligible job.

Saved is a shortlist, not a hire or active invitation.

---

## 3. Smart Matching Requirements

1. Client Premium must be active.
2. The Client must have at least one job in Open status.
3. Select an open job.
4. Optionally select a category and explicit canonical job skills.
5. The service generates and records a match run.

Standard Clients are directed to Client Premium pricing. If no open job exists, the page links to job creation.

---

## 4. Ranked Match Information

Each recommendation can show:

- Final match score and data-confidence badge.
- Skill match, track record, and platform activity breakdown.
- Semantic strengths and explanatory reasons.
- Matched skills and visible skill gaps.
- Average rating and review count.
- Completed contracts and Elo points.

The interface explains the weighting as **45% skill match, 35% track record, and 20% platform activity**. Less historical activity can lower confidence without automatically excluding the Freelancer.

---

## 5. Invitations & Attribution

Opening a matched profile, saving a match, or sending an invitation can record attribution to the match run. The invitation modal can start with the selected job already chosen.

Invited status means an invitation was sent; proposal, negotiation, final offer, and contract steps are still required.

---

## 6. Empty & Failure States

The page distinguishes no saved talent, no directory results, missing open jobs, no Smart Match results, Premium restrictions, and service failures. Smart Matching failures provide Retry and preserve the selected job and filters.
