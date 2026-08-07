---
title: "GigBridge Reset Password"
source: "https://gigbridge.id.vn/auth/reset-password"
description: "Final password-recovery form for setting a new password after OTP verification."
---

# Reset Password

Reset Password is the final step of account recovery. It accepts the verified email and OTP passed from Forgot Password, validates the new credential, and submits the password change to the authentication service.

---

## 1. Page Access & Purpose

- **Route**: `/auth/reset-password`
- **Access**: Public, but a verified email and OTP must be present in navigation state.
- **Purpose**: Replace the account password after successful password-reset verification.
- **Recovery Entry Point**: Users without valid verification state are directed back to `/auth/forgot-password`.

---

## 2. Information Displayed

- **Verified Email**: Shows the account email received from the prior step and does not allow it to be changed here.
- **Verified OTP**: Shows that a password-reset verification code is available from the prior step.
- **New Password**: Accepts the replacement credential and includes a visibility toggle.
- **Confirm New Password**: Must exactly match the new password and has its own visibility toggle.

---

## 3. Password Requirements

The new password must contain:

- At least **8 characters** with no whitespace-only shortcut.
- At least **one uppercase letter**.
- At least **one lowercase letter**.
- At least **one number**.
- At least **one special character**.

The form rejects a password that does not meet the policy or whose confirmation does not match.

---

## 4. Reset Workflow

1. Complete OTP verification on the Forgot Password page.
2. Enter and confirm a policy-compliant new password.
3. Submit the form; it sends the email, OTP, and new password to the reset endpoint.
4. On success, the page shows a completion state and offers a return to Login.
5. Sign in with the new password at `/auth/login`.

---

## 5. Invalid or Failed Requests

- Missing email or OTP produces a verification-required state rather than exposing the reset form as a valid request.
- Expired, rejected, or already-used verification data may be refused by the backend.
- A failed submission leaves the password unchanged and displays the returned error.
- The success screen represents a completed password update; merely reaching this route does not.
