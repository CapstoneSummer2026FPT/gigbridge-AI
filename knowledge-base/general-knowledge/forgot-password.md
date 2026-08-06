---
title: "GigBridge Forgot Password"
source: "https://gigbridge.id.vn/auth/forgot-password"
description: "Email and OTP verification flow used before resetting a GigBridge password."
---

# Forgot Password

**Route:** `/auth/forgot-password`

**Access:** Guests only.

The page verifies account ownership before a password reset. The user enters the account email, requests an OTP code, and submits that code for verification. A resend action becomes available according to the displayed countdown.

After successful OTP verification, the page allows the user to continue to Reset Password. It also provides a link back to Login for users who remember their password.
