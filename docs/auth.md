# Authentication Guide

This document outlines the authentication flow for Zerodha Kite Connect integration.

## Overview

The application requires a valid `access_token` to communicate with the Kite Connect API. This token expires daily (or upon explicit logout) and must be refreshed every morning.

Due to Zerodha's policy and security best practices, the login process requires **manual user intervention** at least once a day. We do not automate the credential entry process.

## Daily Workflow (8:00 AM IST)

### 1. Automated Check
A daily cron job (or GitHub Action) runs `scripts/kite_auth_bootstrap.py`.
- It checks if the current session (stored in `.env` or secrets) is valid.
- If valid, no action is taken.
- If invalid, it flags that authentication is required.

### 2. Manual Login
If authentication is required:
1.  Run the bootstrap script on your server/local machine:
    ```bash
    python scripts/kite_auth_bootstrap.py
    ```
2.  The script will display a login URL.
3.  Open the URL in your browser and log in to Zerodha.
4.  Upon success, Zerodha redirects to your configured callback URL (e.g., `http://localhost:8000/auth/kite/callback`).
5.  The running API server receives the `request_token`, exchanges it for a new `access_token`, and securely persists it to your `.env` file.

### 3. Verification
You can verify the session is valid by running the script again:
```bash
python scripts/kite_auth_bootstrap.py --check-only
```
It should exit with success (status 0).

## Security

-   **Credentials**: `KITE_API_KEY` and `KITE_API_SECRET` are stored in environment variables (or `.env` locally).
-   **Tokens**: `KITE_ACCESS_TOKEN` is rotated daily. It is never committed to version control.
-   **Trading Mode**: The bootstrap process runs in `PAPER` mode context by default. Live trading requires explicit `TRADING_MODE=LIVE`.

## Troubleshooting

-   **Redirect URL Mismatch**: Ensure your Kite Connect app's redirect URL matches your server's address (e.g., `http://localhost:8000/auth/kite/callback`).
-   **Token Expired**: If you see "Token is invalid" errors in logs, run the bootstrap script to refresh the session.
-   **Logging**: Tokens are never printed in logs. The login URL contains the public API Key only.
