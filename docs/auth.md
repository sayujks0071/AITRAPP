# Kite Daily Auth Assistant

The **Kite Daily Auth Assistant** is a tool to ensure your trading application has a valid Zerodha Kite session every day before trading begins.

## Why Manual Login?
Zerodha Kite Connect requires a mandatory manual login flow once every 24 hours. The API enforces this for security; fully automated login (via credentials storage) is against policy and technically restricted.

This tool simplifies the process by automating everything *except* the actual login click.

## Components
1. **`packages/core/auth/kite_auth.py`**: Core module handling session validation, URL generation, and token exchange.
2. **`scripts/kite_auth_bootstrap.py`**: The daily runner script.

## Daily Workflow (8:00 AM IST)

1. **Scheduler** runs `scripts/kite_auth_bootstrap.py`.
2. **Check**: The script verifies if the current `.env` token is still valid.
    - If **Valid**: Exits immediately (Green light).
    - If **Invalid**:
        1. Starts a local web server on port `8080`.
        2. Prints the **Login URL** to the console/logs.
3. **User Action**:
    - Open the URL in your browser.
    - Login to Zerodha.
4. **Callback**:
    - Zerodha redirects to `http://localhost:8080/callback`.
    - The local server receives the `request_token`.
5. **Exchange & Store**:
    - The script exchanges the `request_token` for a long-lived `access_token`.
    - It updates your `.env` file securely.
    - The script exits successfully.

## Setup

### 1. Prerequisites
Ensure your `.env` file exists and has your API keys:
```bash
KITE_API_KEY=your_api_key
KITE_API_SECRET=your_api_secret
KITE_ACCESS_TOKEN=  # Will be filled automatically
```

### 2. Configure Callback URL
In your [Kite Connect Developer Console](https://developers.kite.trade/):
- Set **Redirect URL** to `http://localhost:8080/callback`

### 3. Usage

**Manual Run:**
```bash
PYTHONPATH=. python3 scripts/kite_auth_bootstrap.py
```

**Cron Job (Server/VPS):**
Add to your crontab to run daily at 8:00 AM:
```bash
# Note: Chain a restart command for your main app if necessary (e.g., && systemctl restart trading-app)
0 8 * * * cd /path/to/repo && PYTHONPATH=. python3 scripts/kite_auth_bootstrap.py >> /var/log/kite_auth.log 2>&1
```

**CI/CD (GitHub Actions):**
If running in CI where interactive login isn't possible, the script will print the URL. You can configure it to send a notification (Slack/Telegram) with the URL so you can login on your local machine (if configured to callback to a reachable server) or manually update the secret.

*Note: For CI pipelines, you typically update the GitHub Secret manually.*

## Security
- **No Credentials Stored**: Password and TOTP are never touched by this code.
- **Token Safety**: `access_token` is stored in your environment/secrets manager, not in logs.
- **Live Trading Safety**: By default, the environment runs in `PAPER` mode unless `TRADING_MODE=live` is explicitly set.
