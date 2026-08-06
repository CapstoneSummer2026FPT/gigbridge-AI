---
title: "GigBridge Account Settings"
source: "https://gigbridge.id.vn/settings"
description: "Detailed guide to profile, security, payment, language, theme, portfolio, and work-experience settings."
---

# Account Settings

Settings is the central editor for account information and role-specific profile data. It contains General, Security, Payment, and Preferences tabs; the visible profile and payment tools vary by role.

---

## 1. Page Access & Navigation

- **Route**: `/settings`
- **Access**: Authenticated users.
- **General**: Basic account data and detailed Client or Freelancer profile fields.
- **Security**: Password-change form.
- **Payment**: Wallet shortcuts and bank-account management.
- **Preferences**: Interface language and light/dark theme.

Legacy profile edit routes redirect here. Query parameters may open a specific profile subtab, such as portfolio or experience.

---

## 2. General — Basic Information

- **Avatar**: Upload and crop a profile image before saving it.
- **Account Fields**: Full name, email, phone number, avatar, and preferred language.
- **Save Changes**: Updates the user account first, then the role-specific profile.
- **Feedback**: Shows loading, success, and detailed error messages.

An avatar preview or crop is not permanent until the relevant Save Changes request succeeds.

---

## 3. General — Freelancer Profile

- **Headline, Location & Availability**: Core public professional information.
- **Major**: Required when saving detailed Freelancer information; changing it reloads categories and skills.
- **Categories & Skills**: Selectable taxonomy badges linked to the chosen major/category data.
- **Professional Bio**: If entered, must contain at least **50 words**; the page shows a live word counter.
- **Portfolio**: Create, edit, or delete projects with title, description, project URL, image, and project date. A title is required and future project dates are rejected.
- **Work Experience**: Create, edit, or delete positions with company, job title, start date, optional end date, and description. Required fields and date order are validated.

Portfolio and work-experience deletion requires confirmation before the request is sent.

---

## 4. General — Client Profile

- **Company Name & Location**: Main business identity fields.
- **Company Website**: Public organization URL.
- **Company Size & Industry**: Selected from platform-provided options.
- **Company Description**: If entered, must contain at least **50 words**, with live validation.

Client accounts do not receive Freelancer-only Portfolio and Work Experience subtabs.

---

## 5. Security — Change Password

The Security tab requires the current password, a new password, and confirmation of the new password. It includes password visibility, a Weak/Medium/Strong meter, request loading, success feedback, and backend validation errors.

The form rejects missing values and mismatched confirmation before sending the request. It does not provide a two-factor-authentication setup control.

---

## 6. Payment — Wallet & Bank Accounts

- **Deposit**: Opens `/wallet/deposit` for both Clients and Freelancers.
- **Withdraw**: Opens `/wallet/withdrawals` for Freelancers; this shortcut is hidden from Clients.
- **History**: Opens `/wallet/history`.
- **Bank Account Manager**: Adds and manages bank details used by supported payout workflows.

The Payment tab is a management and navigation area. It does not mark a deposit or withdrawal successful merely because account information was entered.

---

## 7. Preferences

- **Language**: Switch between Tiếng Việt and English.
- **Theme**: Choose the light (`white`) or dark (`black`) interface theme.
- **Immediate Interface Effect**: Preference changes update the application presentation; basic-profile language changes are also saved when the profile form succeeds.

Users should check the success or error message after saving profile information before assuming server-side account data has changed.
