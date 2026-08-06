---
title: "GigBridge Forgot Password"
source: "https://gigbridge.id.vn/auth/forgot-password"
description: "OTP request and verification flow used before a GigBridge password can be reset."
---

# Forgot Password

The Forgot Password page verifies account ownership before allowing a password change. It sends a password-reset OTP to the user's email and validates that code before opening the Reset Password form.

---

## 1. Page Access & Purpose

- **Route**: `/auth/forgot-password`
- **Access**: Public; intended for signed-out users who cannot access their account.
- **Purpose**: Request and verify an OTP for the `password_reset` purpose.
- **Next Page**: `/auth/reset-password`, reached only after the page has a verified email and OTP.

---

## 2. Requesting a Verification Code

1. Enter the email address associated with the GigBridge account.
2. Select the send-code action.
3. The page validates the email format before contacting the authentication service.
4. A successful request displays confirmation and starts a countdown that controls when another code can be sent.

The send action is disabled for an invalid email, while a request is running, after verification is complete, or while the resend countdown is active.

---

## 3. Verifying the OTP

- **OTP Field**: Accepts the code delivered to the supplied email address.
- **Verify Action**: Sends the email, code, and password-reset purpose to the verification endpoint.
- **Verified State**: Locks the relevant verification controls and confirms that the user can proceed.
- **Resend**: A new code can be requested when permitted if the original email does not arrive or expires.

An empty or rejected code does not allow the user to continue.

---

## 4. Continuing to Reset Password

After successful verification, the page sends the email and OTP to `/auth/reset-password` through navigation state. This prevents the normal user flow from treating an unverified email as approved.

Opening Reset Password without this state results in a verification-required message and a link back to Forgot Password.

---

## 5. Errors & Navigation

- Invalid email addresses are rejected before the request is sent.
- Delivery, verification, expiry, and server errors are displayed on the page without changing the password.
- The user can return to `/auth/login` at any time.
- A success message only confirms code delivery or OTP verification; it does not mean the account password has already changed.
