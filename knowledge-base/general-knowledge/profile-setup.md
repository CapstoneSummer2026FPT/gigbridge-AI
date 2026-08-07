---
title: "GigBridge Profile Setup"
source: "https://gigbridge.id.vn/onboarding/profile-setup"
description: "Required two-step onboarding for new GigBridge Client and Freelancer accounts."
---

# Profile Setup

Profile Setup is the mandatory role-specific onboarding flow shown after registration. It collects the minimum professional or company information required before the account can enter its dashboard and use setup-protected features.

---

## 1. Page Access & Progress

- **Route**: `/onboarding/profile-setup`
- **Access**: Authenticated Client or Freelancer accounts whose setup is incomplete.
- **Format**: Two steps with a visible progress indicator, Back, Continue, and Complete Profile controls.
- **Completion Result**: Marks profile setup as complete and redirects Clients to `/client/dashboard` or Freelancers to `/freelancer/dashboard`.

The Continue or Complete action remains unavailable until the required fields for the current step are present.

---

## 2. Client — Company Information

The first Client step collects:

- **Company Name (Required)**: The organization or hiring identity displayed on the Client profile.
- **Industry (Required)**: Selected from the industries supplied by the platform, with fallback values available if necessary.
- **Company Website**: Optional public website, entered as a URL.
- **Company Size**: Selected from the available company-size options.

Company name and industry are required before moving to the second step.

---

## 3. Client — Additional Details

- **Location (Required)**: A city and country entered manually or selected with the location picker.
- **Company Description**: An overview of the company, its work, and the type of talent it hires.

Submitting creates or updates the Client profile using the entered company information. A failed request keeps the user on the page and shows the returned error.

---

## 4. Freelancer — Professional Information

- **Professional Title (Required)**: A concise headline such as Full-Stack Developer or UI/UX Designer.
- **Major (Required)**: The top-level professional discipline loaded from the GigBridge taxonomy.
- **Categories (At Least One Required)**: Specializations linked to the selected major.

Changing the major reloads the related categories and clears selections that no longer apply. If taxonomy loading fails, the page provides a Retry action.

---

## 5. Freelancer — Additional Details

- **Location (Required)**: Entered directly or chosen through the location picker.
- **Biography (Required)**: A professional summary explaining skills, experience, and differentiators.
- **Availability**: Available for more than 30 hours per week, busy for fewer than 30 hours, or not available.

The final Freelancer step requires both location and biography. Completing it makes the professional profile available to the rest of the platform.

---

## 6. Submission & Error States

- The page disables navigation actions while the profile is being submitted.
- Loaded industries, company sizes, majors, and categories come from platform services where available.
- Validation happens per step; completing step one does not submit the profile by itself.
- A success redirect indicates that the setup flag and role profile were saved. If an error appears, the user should correct the stated field or retry the request.
