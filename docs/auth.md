# Kite Authentication Guide

This document outlines the daily authentication process for the trading application using Zerodha Kite Connect.

## Overview

Due to [Kite Trade regulations](https://kite.trade/docs/connect/v3/exceptions/), full automation of the login process is **not permitted**. A manual login is required once every 24 hours (typically in the morning) to generate a new `access_token`.

This repository includes a "Kite Daily Auth Assistant" to streamline this process securely.

## Daily Auth Flow (8:00 AM IST)

The system is designed to be bootstrapped daily at 8:00 AM IST.

1.  **Automated Check**: A scheduled job (GitHub Actions or Cron) runs `scripts/kite_auth_bootstrap.py`.
2.  **Session Validation**: The script checks if the existing `access_token` is valid.
    *   If valid, the script exits successfully.
    *   If invalid/expired, it initiates the manual login flow.
3.  **Manual Login**:
    *   The script prints a **Login URL** and starts a local callback server.
    *   **User Action**: You must click the URL and log in to Zerodha on your browser.
4.  **Token Exchange**:
    *   Upon successful login, Zerodha redirects to the callback URL (e.g., `http://localhost:8000/`).
    *   The local server captures the `request_token`.
    *   The script exchanges it for a long-lived `access_token`.
5.  **Persistence**:
    *   The new `access_token` is securely stored in the `.env` file (or encrypted store).
    *   The application can now be started/restarted with the valid session.

## Usage

### 1. Manual Bootstrap (Local/VPS)

Run the bootstrap script from the repository root:

```bash
# Check status only (exit 0 if valid, 1 if invalid)
python scripts/kite_auth_bootstrap.py --check-only

# Run interactive bootstrap (starts server if needed)
python scripts/kite_auth_bootstrap.py
```

Follow the on-screen instructions.

### 2. GitHub Actions (CI/Cloud)

The `.github/workflows/daily_auth.yml` workflow runs daily at 8:00 AM IST.
*   It checks if the session is valid.
*   If invalid, it creates a **GitHub Issue** alerting the operator to perform the manual login on the server.
*   **Note**: CI cannot perform the login for you; it can only alert you.

## Security & Safety

*   **No Credential Storage**: We do not store your Zerodha password or TOTP.
*   **Token Safety**: Access tokens are stored in `.env` (ensure this file is gitignored and secured).
*   **Trading Mode**: By default, the bootstrap script ensures `APP_MODE` is set to `PAPER` unless explicitly overridden.
*   **Logs**: `request_token` and `access_token` values are masked or omitted from logs.

## Troubleshooting

*   **Port in use**: If port 8000 is in use, the script will warn you. You can specify a different port:
    ```bash
    python scripts/kite_auth_bootstrap.py --port 8090
    ```
    *Note: Your Kite Connect app must allow the redirect URI with the corresponding port.*

*   **API Server Running**: If the main API server is already running and handling callbacks (at `/auth/kite/callback`), the bootstrap script might conflict if trying to bind the same port. Use `--check-only` or ensure the API server is stopped during bootstrap if they share the port.
