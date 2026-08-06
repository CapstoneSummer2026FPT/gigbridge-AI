---
title: "GigBridge Client Profile"
source: "https://gigbridge.id.vn/profile/client/:id"
description: "Public-facing Client profile with company information, jobs, reputation, reviews, sharing, and reporting."
---

# Client Profile

The Client Profile helps Freelancers and other permitted users evaluate the organization behind a project. It combines saved company details with reputation, jobs, and reviews connected to the selected Client ID.

---

## 1. Page Access & Identity

- **Route**: `/profile/client/:id`
- **Access**: Authenticated users; the `:id` identifies the Client whose profile is loaded.
- **Owner View**: The profile owner receives an Edit Profile action that opens `/settings`.
- **Other-User View**: Provides sharing and reporting controls instead of owner-only editing.

If the ID is missing, the profile cannot be loaded, or the service returns an error, the page shows an error state and a Back action.

---

## 2. Company Header

- **Client Name & Avatar**: Taken from the associated user account.
- **Company Name**: Displayed as the main organization identity when available.
- **Location**: Shows the saved company location.
- **Website**: Opens the company website in a new tab; a missing protocol is normalized to HTTPS.
- **Industry & Company Size**: Shown from the saved Client profile.

---

## 3. Company Overview & Reputation

- **Bio/Overview**: Displays the company description supplied by the Client.
- **Company Information**: Repeats key business details such as location, website, size, industry, and account email in a structured section.
- **Elo Point**: Shows the platform reputation score and verified indicator presented by the profile.
- **Profile Strength**: Visualizes how complete the Client profile is.

Reputation and profile-strength indicators are informational; they do not guarantee a project outcome or payment approval.

---

## 4. Jobs & Reviews

- **Job List**: Shows jobs associated with the Client and provides navigation into job browsing/details where supported.
- **Review Summary**: Displays the average rating and number of Freelancer reviews.
- **Review Details**: May include project context, date, overall stars, communication, quality, timeliness, and written comments.
- **Anonymous Reviews**: Hide the reviewer's identity and disable profile navigation for that reviewer.
- **Pagination**: Allows movement through multiple review entries.

An empty review section means no review records were returned for the Client; it is not an automatically negative rating.

---

## 5. Share & Report

- **Share Profile**: Copies the current profile URL to the clipboard.
- **Report User**: Opens the report modal for a signed-in viewer who is not the profile owner.
- **Submitted Report**: Disables repeat submission through the same control and changes the action to a reported state.

Reporting sends information for platform review; it does not immediately suspend or remove the reported account.
