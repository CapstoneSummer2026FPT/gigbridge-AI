---
title: "GigBridge Login"
source: "https://gigbridge.id.vn/auth/login"
description: "Detailed guide to signing in with email or Google and understanding GigBridge login redirects and errors."
---

# Login

The Login page authenticates existing GigBridge users. It supports standard email-and-password access and Google OAuth, then directs each account to the correct onboarding, dashboard, or administration area.

---

## 1. Page Access & Purpose

- **Route**: `/auth/login`
- **Access**: Guests only. An authenticated user is redirected away from the public authentication page.
- **Purpose**: Restore a GigBridge session and load the user's assigned role and profile-setup state.
- **Available Roles**: Client, Freelancer, and Administrator accounts can sign in through this page.

---

## 2. Email & Password Login

The standard form contains:

- **Email Address**: The email registered with the account.
- **Password**: The account password, with a visibility toggle for checking the entered value.
- **Sign In Button**: Remains unavailable until both email and password contain a value.
- **Forgot Password Link**: Opens `/auth/forgot-password` to start OTP-based password recovery.
- **Create Account Link**: Opens `/auth/signup` for users who have not registered.

Submitting the form calls the authentication service. While the request is running, the form displays a loading state and prevents duplicate submissions.

---

## 3. Continue with Google

1. Select **Continue with Google** and choose a Google account in the provider window.
2. GigBridge exchanges the returned authorization code for an application session.
3. The platform reads the account's existing role. A role previously selected during signup may be used when completing a new Google registration.
4. If the Google account has no valid GigBridge role, the page stops the login and asks the user to register with a role or contact support.

Google login depends on the Google Identity service and the configured OAuth client being available. Provider or configuration errors are displayed separately from email-login errors.

---

## 4. Redirects After Successful Login

- **Administrator**: Redirected to `/admin`.
- **Client with Completed Setup**: Redirected to `/client/dashboard`.
- **Freelancer with Completed Setup**: Redirected to `/freelancer/dashboard`.
- **Incomplete Client or Freelancer Profile**: Redirected to `/onboarding/profile-setup` before protected work features can be used.

The temporary role selection saved during signup is cleared after a successful login.

---

## 5. Errors & Safe Retry

- Incorrect credentials, blocked requests, and server failures leave the user on the Login page and display the returned error.
- An account without a recognized role is not sent to a normal dashboard.
- A failed request does not count as a successful session, even if form values remain visible.
- Users can correct the entered information and retry without navigating away.
