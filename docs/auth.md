# Kite Authentication Guide

This document describes the authentication flow for Zerodha Kite Connect, ensuring secure and compliant session management.

## Overview

The authentication system is designed to:
1.  **Validate Session**: Automatically check if the current `access_token` is valid.
2.  **Manual Login**: Prompt the user for manual login (as per [Kite Trade regulations](https://kite.trade/docs/connect/v3/user/#login-flow)) if the session is invalid.
3.  **Secure Exchange**: Automatically exchange the `request_token` for an `access_token`.
4.  **Persistence**: Store the `access_token` securely in the `.env` file for the application to use.
5.  **Safety**: Default to `PAPER` trading mode and block live orders if authentication is missing.

## Daily Auth Bootstrap (8:00 AM IST)

A dedicated script `scripts/kite_auth_bootstrap.py` handles the daily authentication ritual.

### Usage

Run the bootstrap script:

```bash
python scripts/kite_auth_bootstrap.py
```

### Options

*   `--check-only`: Only checks if the session is valid and exits with 0 (valid) or 1 (invalid). Does not prompt for login.
*   `--port PORT`: Specify the port for the local callback receiver (default: 8000).

### Workflow

1.  **Check**: The script checks if `KITE_ACCESS_TOKEN` in `.env` is valid.
2.  **Prompt**: If invalid, it prints a login URL.
3.  **Login**: Open the URL in your browser and log in to Zerodha.
4.  **Callback**:
    *   **If API Server is running**: The API server receiving the callback at `/auth/kite/callback` will exchange and store the token. The script detects this via polling.
    *   **If API Server is NOT running**: The script starts a temporary local server to capture the callback directly.
5.  **Success**: The `.env` file is updated with the new `KITE_ACCESS_TOKEN`.

## Setup & Configuration

### Prerequisites

Ensure your `.env` file has the following Kite credentials:

```bash
KITE_API_KEY=your_api_key
KITE_API_SECRET=your_api_secret
KITE_ACCESS_TOKEN=  # Will be populated automatically
KITE_USER_ID=your_user_id
```

### Callback URL

In your [Kite Developer Console](https://developers.kite.trade/apps), set the **Redirect URL** to:

```
http://localhost:8000/auth/kite/callback
```

(Or your production domain if applicable).

## Automation (Cron)

To automate the daily check, add a cron job on your server (run `crontab -e`):

```bash
# Run Auth Bootstrap at 8:00 AM IST daily
0 8 * * * cd /path/to/repo && /path/to/venv/bin/python scripts/kite_auth_bootstrap.py >> logs/auth_bootstrap.log 2>&1
```

*Note: Since manual login is required, this script will mostly serve to notify you or wait for your action if the token is expired.*

## Safety Rails

*   **Trading Mode**: The system defaults to `PAPER` mode. `LIVE` mode must be explicitly enabled.
*   **Order Blocking**: In `LIVE` mode, order placement is blocked if the `access_token` is missing or invalid.
*   **Secrets**: `request_token` is masked in logs. Access tokens are never printed to console.
