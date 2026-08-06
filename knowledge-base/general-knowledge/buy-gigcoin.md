---
title: "GigBridge Buy GigCoin Packages"
source: "https://gigbridge.id.vn/buy-gigcoin"
description: "Current package-selection screen and its relationship to the real wallet top-up flow."
---

# Buy GigCoin Packages

**Route:** `/buy-gigcoin`

**Access:** Signed-in users with completed setup.

This screen displays fixed USD-denominated example packages and a package-selection interface. In the current frontend, its Purchase action uses simulated processing and returns to the previous page; it does not call the wallet top-up API or credit GigCoin.

For an actual wallet top-up, users should use **Wallet Deposit** at `/wallet/deposit`, which creates a PayOS checkout in VND and synchronizes the resulting wallet transaction.
