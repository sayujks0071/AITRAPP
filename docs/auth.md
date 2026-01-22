# Kite Connect Authentication & Security

This document outlines the authentication flow for the trading application, designed to meet Zerodha Kite Connect's security requirements and ensure safe operations.

## Why Manual Login?

Per [Kite Connect API regulations](https://kite.trade/docs/connect/v3/user/), fully automated login (using Selenium, saving passwords/TOTP) is **strictly prohibited**. The API mandates a manual user-initiated login once every 24 hours to generate a new session.

We adhere to this by implementing a **"Daily Auth Bootstrap"** process that requires a single manual intervention each morning.

## Daily Authentication Flow (8:00 AM IST)

We have a dedicated script `scripts/kite_auth_bootstrap.py` that manages the daily session.

### The Workflow

1.  **Scheduled Check**: At 8:00 AM IST, the scheduler runs the bootstrap script.
    *   Command: `python scripts/kite_auth_bootstrap.py`
2.  **Validation**: The script checks if the existing `Kite Connect` session is still valid.
    *   If valid: The script exits successfully (nothing to do).
    *   If invalid: It proceeds to the login flow.
3.  **Manual Login**:
    *   The script prints a **Login URL** to the console (or sends it via notification/GitHub Issue).
    *   **User Action**: You open the URL in your browser and log in to Zerodha.
4.  **Token Capture**:
    *   Upon successful login, Zerodha redirects to the configured `redirect_uri` (e.g., your API server or local callback receiver).
    *   The application captures the `request_token`.
5.  **Exchange & Persist**:
    *   The application exchanges the `request_token` for a long-lived `access_token` (valid for 24h).
    *   The new `access_token` is securely stored in the `.env` file (or secret store).
6.  **Ready**: The trading system is now authorized for the day.

## Scheduler Setup

### Option 1: VPS / Server (Cron)

Add the following entry to your crontab to run daily at 8:00 AM IST:

```bash
# Run daily at 08:00 IST (UTC+5:30) => 02:30 UTC
30 2 * * * cd /path/to/app && TRADING_MODE=paper python scripts/kite_auth_bootstrap.py >> /var/log/kite_auth.log 2>&1
```

### Option 2: GitHub Actions

If running via GitHub Actions, use the provided workflow `.github/workflows/daily_auth.yml`.
This workflow checks the session and opens a GitHub Issue if login is required.

## Security & Safety Rails

### Secret Storage
*   **No Credentials Stored**: We do **not** store your Zerodha password or TOTP secret.
*   **Token Encryption**: The `access_token` is stored in the environment (`.env`) which should be secured with file permissions (600).
*   **Logs**: Tokens are masked in application logs.

### Live Trading Safety
*   **Default to Paper**: The system defaults to `PAPER` mode unless `TRADING_MODE=live` or `APP_MODE=LIVE` is explicitly set in the environment.
*   **Order Blocking**: The execution engine explicitly blocks any order placement if the `access_token` is missing or invalid, ensuring no "zombie" processes try to trade without auth.
