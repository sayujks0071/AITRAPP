# Kite Daily Auth Assistant

The **Kite Daily Auth Assistant** is a self-contained tool (`scripts/kite_auth_bootstrap.py`) designed to ensure your trading application has a valid Zerodha Kite session every day before trading begins.

## Features
- **Manual Login Enforcement**: Complies with Zerodha's policy by requiring manual login.
- **Auto Token Exchange**: Automates the exchange of `request_token` for `access_token`.
- **Secure Persistence**: Updates your local `.env` file directly without exposing secrets in logs.
- **Safety**: Checks `TRADING_MODE` and defaults to logging warnings if in LIVE mode.

## Daily Workflow (8:00 AM IST)

1. **Scheduler** runs `scripts/kite_auth_bootstrap.py`.
2. **Check**: The script verifies if the current `.env` token is valid via a lightweight API call (`kite.profile()`).
    - If **Valid**: Exits immediately (Green light).
    - If **Invalid**:
        1. Starts a local web server (default port 8080).
        2. Prints the **Login URL**.
3. **User Action**:
    - Open the URL in your browser.
    - Login to Zerodha.
4. **Callback**:
    - Zerodha redirects to `http://localhost:8080/callback`.
    - The local server captures the `request_token`.
5. **Exchange & Store**:
    - The script exchanges the token.
    - Updates `.env` with:
        - `KITE_ACCESS_TOKEN`
        - `KITE_USER_ID`
        - `KITE_TOKEN_CREATED_AT_ISO`
    - Exits successfully.

## Configuration

### Environment Variables (.env)
Required:
```bash
KITE_API_KEY=your_api_key
KITE_API_SECRET=your_api_secret
```

Managed (Updated by script):
```bash
KITE_ACCESS_TOKEN=...
KITE_USER_ID=...
KITE_TOKEN_CREATED_AT_ISO=...
```

Optional Overrides (Environment or .env):
- `KITE_AUTH_HOST`: Host for callback server (default: `127.0.0.1`)
- `KITE_AUTH_PORT`: Port for callback server (default: `8080`). Also checks `AUTH_CALLBACK_PORT`.
- `TRADING_MODE`: `paper` (default) or `live`.

### Kite Developer Console
Ensure your App's **Redirect URL** matches your host/port:
- Default: `http://localhost:8080/callback`

## Usage

**Manual Run:**
```bash
python3 scripts/kite_auth_bootstrap.py
```

**Cron Job (Server/VPS):**
Add to your crontab to run daily at 8:00 AM:
```bash
# Note: Chain a restart command for your main app if necessary
0 8 * * * cd /path/to/repo && python3 scripts/kite_auth_bootstrap.py >> /var/log/kite_auth.log 2>&1
```

## Security
- **No Credentials Stored**: Password and TOTP are never touched.
- **Token Safety**: Access tokens are stored only in `.env`.
- **Live Trading Safety**: Warns if running in LIVE mode.
