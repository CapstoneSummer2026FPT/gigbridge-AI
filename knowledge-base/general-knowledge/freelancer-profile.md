---
title: "GigBridge Freelancer Profile"
source: "https://gigbridge.id.vn/profile/freelancer/:id"
description: "Detailed Freelancer profile for professional identity, expertise, work history, portfolio, reviews, saving, invitations, and reports."
---

# Freelancer Profile

The Freelancer Profile is the main evaluation page for a professional on GigBridge. It combines identity and availability with taxonomy, skills, experience, portfolio evidence, reputation, and contract reviews.

---

## 1. Page Access & Viewer Controls

- **Route**: `/profile/freelancer/:id`
- **Access**: Authenticated users; `:id` selects the Freelancer profile.
- **Owner Action**: Edit Profile opens Settings.
- **Client Actions**: Invite to Job and Save/Unsave Freelancer are available to eligible Client viewers.
- **General Actions**: Copy the profile link or report the user.

A missing ID, failed request, or unavailable profile produces an error state with a Back action.

---

## 2. Professional Header

- **Name & Avatar**: Loaded from the user's account.
- **Premium Badge**: Appears when the Freelancer has the corresponding Premium state.
- **Professional Title**: Uses the saved title or major name.
- **Location & Major**: Summarize where the Freelancer is based and their main discipline.
- **Availability**: Shows full-time, part-time, unavailable, or the platform's available state according to the saved value.

---

## 3. Expertise & Profile Strength

- **Biography**: The Freelancer's professional overview.
- **Categories**: Selected specializations under the Freelancer's major.
- **Skills**: Individual skills shown as badges.
- **Elo Point**: Platform reputation score with the profile's verified presentation.
- **Profile Strength**: Completeness indicator based on available profile information.

These fields are maintained from Settings; viewing a profile does not change the Freelancer's taxonomy or availability.

---

## 4. Work Evidence

- **Recently Worked**: Summarizes recent engagement or experience records when available.
- **Portfolio Projects**: Displays saved portfolio entries with title, image, description, link, and project date where provided.
- **Work Experience**: Lists positions with company, job title, dates, and descriptions.
- **Owner Shortcuts**: The owner can jump to the Settings portfolio or experience subtab to add records.

Empty portfolio or experience sections indicate that no corresponding records were returned; sample-looking placeholders should not be treated as verified work history.

---

## 5. Client Reviews

- **Summary**: Average rating and total Client review count.
- **Review Cards**: May show reviewer, project context, date, overall rating, communication, quality, timeliness, and comments.
- **Anonymous Option**: Anonymous reviewers are labeled without exposing or linking their identity.
- **Pagination**: Used when the Freelancer has multiple reviews.

Reviews appear after eligible contract activity and should be interpreted with their project context and count.

---

## 6. Invitations, Saving & Reporting

1. A Client can select **Invite to Job** to open a modal and choose an eligible job.
2. **Save** bookmarks the Freelancer for later review; selecting it again removes the saved state.
3. **Share** copies the current browser URL.
4. **Report User** opens the reporting flow and changes to a reported state after successful submission.

An invitation is not a contract or hire. The Freelancer must still respond and the parties must complete the proposal, offer, and contract workflow.
