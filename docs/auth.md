# Kite Daily Auth Assistant

**"Kite Daily Auth Assistant"** is a security-first session bootstrapper for the trading app using **Zerodha Kite Connect**. It runs daily at 8:00 AM IST to ensure a valid `access_token` exists before the market opens.

## Why Manual Login?

Zerodha Kite Connect **mandates** a manual login once every 24 hours to generate a new session.
*   **Fully automated login (using Selenium/Headless) is strictly prohibited** by Zerodha and can lead to account bans.
*   We automate the *token exchange* and *storage*, but the *credential entry* must be done by a human.

## Daily Workflow (8:00 AM IST)

1.  **Scheduler** triggers `scripts/kite_auth_bootstrap.py`.
2.  **Check**: The script checks if the current `access_token` in `.env` is valid.
    *   If **Valid**: Script exits (Success). App starts normally.
    *   If **Invalid**:
        *   Script generates a **Login URL**.
        *   Script starts a temporary **Callback Server** on port 8080.
        *   User is prompted to click the Login URL.
3.  **User Action**:
    *   User logs in to Zerodha in the browser.
    *   User approves the app.
4.  **Callback**:
    *   Zerodha redirects to `http://localhost:8080/callback?request_token=...`.
    *   The temporary server captures the `request_token`.
5.  **Exchange & Store**:
    *   Script exchanges `request_token` for a new `access_token`.
    *   Script updates `.env` with the new token.
    *   Script exits (Success).

## Setup

### Prerequisites
*   Zerodha Kite Connect API Key & Secret.
*   Redirect URI in Zerodha Developer Console set to: `http://localhost:8080/callback`

### Scheduling

#### On VPS / Server
Add this cron job to run at 8:00 AM IST:

```bash
# Run Auth Bootstrap at 8:00 AM IST (2:30 AM UTC)
30 2 * * * cd /path/to/repo && python scripts/kite_auth_bootstrap.py
```

#### GitHub Actions
Since GitHub Actions cannot open a browser for you, the workflow sends a notification (e.g., creates an Issue) telling you to run the bootstrap script locally or on the server.

## Security & Safety

*   **No Credential Storage**: We never store your Zerodha password or TOTP.
*   **Token Safety**: Access tokens are stored in `.env` (or secrets manager), never printed to logs.
*   **Paper Default**: `TRADING_MODE` defaults to `PAPER` to prevent accidental live trading.
*   **Live Gating**: Live trading requires `TRADING_MODE=live` AND `I_UNDERSTAND_LIVE_TRADING=true`.
