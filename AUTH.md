# 🔐 Authentication Guide

AITRAPP uses Zerodha Kite Connect for market data and trading execution. This guide explains how to authenticate correctly.

## Quick Start (Daily Routine)

Every morning before trading (or when your token expires), run:

```bash
python3 scripts/kite_auth_bootstrap.py
```

This will:
1. Open your browser to the Kite login page.
2. Wait for you to log in.
3. Automatically capture the secure token.
4. Update your `.env` file with the new credentials.

### Modes

By default, the script sets up for **PAPER** trading.

#### Live Trading
If you intend to trade with real money:

```bash
python3 scripts/kite_auth_bootstrap.py --mode LIVE
```

You will be asked to type `LIVE` to confirm.

---

## Prerequisites

Before running the bootstrap script, ensure that the redirect URL is registered in your Kite Connect app:

1. Visit https://developers.kite.trade/apps
2. Select your app
3. Add **exactly** `http://localhost:8080/callback` to the list of **Redirect URLs** (the exact URL format is required)
4. Save the changes

Without this, the authentication flow will fail after you log in to Kite.

---

## Manual Method (Legacy Fallback)

Use this only when the `kite_auth_bootstrap.py` flow cannot be used (for example, on a headless server or when debugging authentication issues).

The legacy script achieves the *same final result* as the bootstrap script (a fresh Kite access token stored in your `.env`), but it does **not** open a browser or run a local callback server. Instead, you manually copy-paste the request token.

Steps:
1. Run the legacy script:
   ```bash
   python3 get_kite_token.py
   ```
2. Follow the on-screen instructions to manually copy-paste the request token from the Kite URL into the terminal.
3. After completion, the `.env` file will be updated just as if you had used `kite_auth_bootstrap.py`.

The legacy script is maintained for backward compatibility and headless/CI use cases; for normal desktop use, prefer `kite_auth_bootstrap.py`.

---

## Troubleshooting

### Port 8080 in use
If you see "Port 8080 is busy", ensure no other instance of the script or another service is using that port.
```bash
lsof -i :8080
kill <PID>
```

### Invalid Token / Session Expired
Kite tokens expire daily (usually around 7:30 AM IST next day) or if you log out from Kite web elsewhere. Simply re-run the bootstrap script.

### Environment Variables
The script manages these variables in your `.env` file:
- `KITE_ACCESS_TOKEN`: The session token.
- `KITE_USER_ID`: Your Zerodha user ID.
- `KITE_TOKEN_CREATED_AT_ISO`: Timestamp of last generation.

Do **not** commit `.env` to version control.
