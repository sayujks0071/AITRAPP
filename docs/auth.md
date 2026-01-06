# Kite Daily Auth Assistant

This document outlines the daily authentication flow for Zerodha Kite Connect using the `Kite Daily Auth Assistant`.

## Overview

The system runs a daily job at **08:00 AM IST** to ensure a valid `access_token` is available for trading.
Due to Zerodha's security requirements, full automation is not possible; a manual login is required once every 24 hours.

## Workflow

1.  **Scheduled Job**: At 08:00 AM IST, `scripts/kite_auth_bootstrap.py` runs.
2.  **Session Check**: It checks if the current `access_token` (stored in `.env`) is valid.
    *   If valid: The script exits (Success).
    *   If invalid/expired: The script initiates the manual login flow.
3.  **Manual Login**:
    *   The script prints the **Login URL**.
    *   It starts a local web server (default port `8080`).
    *   The user visits the Login URL and authenticates with Zerodha.
4.  **Token Exchange**:
    *   Zerodha redirects to `http://localhost:8080/callback?request_token=...`.
    *   The local server captures the `request_token`.
    *   The script exchanges it for a long-lived `access_token`.
5.  **Persistence**:
    *   The `access_token` is securely stored in the `.env` file (local dev/VPS).
    *   The trading application reads this token on startup.

## Usage

### Manual Trigger

You can run the bootstrap script manually at any time:

```bash
python scripts/kite_auth_bootstrap.py
```

**Options:**
*   `--check-only`: Only check session validity and exit. Returns exit code 0 if valid, 1 if invalid (and prints Login URL). Useful for CI/CD checks.
*   `--port PORT`: Specify the local port to listen on (default: 8080).

Example:
```bash
python scripts/kite_auth_bootstrap.py --port 9090
```

### Scheduled (Cron)

For a VPS or always-on server, add this to your crontab:

```bash
# Run at 08:00 AM IST (UTC+5:30 -> 02:30 UTC)
30 2 * * * cd /path/to/repo && TRADING_MODE=paper python scripts/kite_auth_bootstrap.py >> auth.log 2>&1
```

### GitHub Actions

In CI/CD environments (GitHub Actions), the script cannot perform the interactive login.
The workflow `daily_auth.yml` checks the token status using `--check-only`. If invalid, it will create a GitHub Issue to notify the team to perform the manual login on the deployment server.

## Security

*   **No Credential Storage**: Passwords and TOTP are never stored or automated.
*   **Token Safety**: Access tokens are stored in environment variables/files, not in code.
*   **Logs**: Secrets are never printed to logs.
*   **Safety Rails**: `TRADING_MODE` defaults to `PAPER` to prevent accidental live trading during auth.
