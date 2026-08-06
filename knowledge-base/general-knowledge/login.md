---
title: "GigBridge Login"
source: "https://gigbridge.id.vn/auth/login"
description: "How users sign in to GigBridge and where they are sent after authentication."
---

# Login

**Route:** `/auth/login`

**Access:** Guests only. Signed-in users are redirected to the appropriate dashboard.

Users can sign in with an email address and password or continue with Google. The form includes password visibility, a Remember me option, a link to password recovery, and a link to create an account.

After successful authentication, administrators go to the admin area. Clients and freelancers who have not completed setup go to Profile Setup; completed accounts go to their role dashboard.

Failed authentication stays on the page and displays the returned error. Google sign-in depends on the Google identity service being available.
