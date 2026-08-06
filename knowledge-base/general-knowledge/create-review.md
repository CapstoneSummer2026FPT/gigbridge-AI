---
title: "GigBridge Create Review"
source: "https://gigbridge.id.vn/reviews/create"
description: "Participant form for reviewing the other party after eligible project work."
---

# Create Review

Create Review lets an eligible contract participant evaluate the other party after project work. The form is contract-scoped and changes its criteria wording depending on whether the reviewer is the client or freelancer.

---

## 1. Access & Contract Checks

- **Route**: `/reviews/create?contractId=:contractId` (the page also accepts the `contract` query key).
- **Users**: The contract's client or freelancer.
- **Eligibility**: The loaded contract must allow the current user to review.
- **Duplicate prevention**: If `hasReviewedByCurrentUser` is true, or the current session just submitted, the form is replaced by an already-reviewed state.

The page identifies both the review recipient and project title so feedback is not accidentally submitted for the wrong agreement.

---

## 2. Rating Criteria

Every criterion uses a required 1–5 star control:

- **Communication** for both roles.
- **Work quality** when a client reviews a freelancer; **requirement clarity** when a freelancer reviews a client.
- **On-time delivery** for a freelancer; **approval and payment timeliness** for a client.

The interface displays the live arithmetic average. The stored overall rating is the rounded average of the three named sub-ratings; users do not enter a separate overall score.

---

## 3. Comment & Identity

The optional comment is trimmed and limited to 1,000 characters. Its placeholder is role-specific. Reviews are submitted with `isAnonymous: false`, and the identity notice explains that the feedback is associated with the reviewer rather than offering an anonymous toggle.

---

## 4. Submission

All three criteria must be selected. While the request is processing, repeated submission and cancellation are disabled. API validation failures remain visible in the form. A successful response shows completion and provides navigation back to the contract workspace. Reviews should describe the completed collaboration; contract reports and disputes remain the correct channels for issues that need operational or financial resolution.
