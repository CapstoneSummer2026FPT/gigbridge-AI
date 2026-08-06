---
title: "GigBridge Signup"
source: "https://gigbridge.id.vn/auth/signup"
description: "Detailed guide to selecting a role, verifying an email, accepting policies, and creating a GigBridge account."
---

# Signup

Signup is a role-first registration flow for new Clients and Freelancers. Email registration requires one-time-password verification, while Google registration uses the selected role to create the correct account type.

---

## 1. Page Access & Purpose

- **Route**: `/auth/signup`
- **Access**: Guests only.
- **Purpose**: Create a Client or Freelancer account and continue directly to mandatory Profile Setup.
- **Role Permanence**: The chosen role controls onboarding fields, dashboards, permissions, and later workflows. Users should select the role that represents how they intend to use GigBridge.

---

## 2. Choose an Account Role

The first step presents two choices:

- **Client**: For users or businesses that post project requests, evaluate proposals, create contracts, and fund milestone escrow.
- **Freelancer**: For professionals who build a profile, find jobs, submit proposals, complete interviews, and deliver contracted work.

Selecting a role stores it temporarily for the registration flow and opens the account form. The user can go back to change the selection before registration is completed.

---

## 3. Email Registration Fields

- **Full Name**: Required before account creation.
- **Email Address**: Must use a valid email format and must be verified.
- **OTP Code**: A one-time verification code sent for the `signup` purpose.
- **Password**: Required and can be shown or hidden with the visibility control.
- **Policy Consent**: The user must accept the GigBridge policy agreement. Links to the Terms of Service and Privacy Policy open in separate browser tabs.

The Create Account action remains unavailable until the email is verified and the required name and password fields are present.

---

## 4. Email Verification Workflow

1. Enter a valid email address and request an OTP.
2. GigBridge sends a signup verification code and starts the resend countdown.
3. Enter the received code and select **Verify OTP**.
4. Successful verification returns a verification ticket used during final account creation.
5. If necessary, use **Resend OTP** after the relevant control becomes available.

Changing or reverifying the email resets the prior verification state. Account creation cannot continue with an unverified email or a missing verification ticket.

---

## 5. Google Registration

After choosing Client or Freelancer, the user may register with Google instead of the email form. GigBridge sends the selected role with the Google authorization result, creates the session, and directs the new account to Profile Setup.

If the Google provider is unavailable, blocked, or misconfigured, the page displays an error and keeps the user in the registration flow.

---

## 6. Completion & Errors

- **Successful Registration**: Displays a confirmation and redirects to `/onboarding/profile-setup`.
- **Policy Not Accepted**: Focuses the consent area and explains that acceptance is required.
- **Invalid Email or OTP**: Keeps the form open and displays the returned validation message.
- **Duplicate or Rejected Account**: Does not create a session; the user can correct the form or use the Login link if the account already exists.
- **Loading Protection**: Registration, OTP, and Google actions use loading/disabled states to reduce duplicate requests.
