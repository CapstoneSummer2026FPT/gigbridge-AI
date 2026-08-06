---
title: "GigBridge Reset Password"
source: "https://gigbridge.id.vn/auth/reset-password"
description: "How a verified user chooses and confirms a new GigBridge password."
---

# Reset Password

**Route:** `/auth/reset-password`

**Access:** Guests with valid password-reset verification state.

The user enters and confirms a new secure password. GigBridge first checks that the reset request is valid; opening the page without the required verification state cannot complete a reset.

The passwords must match and satisfy the form's security validation. After a successful update, the page confirms the reset and directs the user to Login with the new credentials.
