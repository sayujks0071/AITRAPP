# 🔐 Authentication Guide

AITRAPP uses Zerodha Kite Connect for market data and trading execution. This guide explains how to authenticate correctly.

## Prerequisites

**IMPORTANT**: Before running the authentication script, you must register the callback URL in your Kite Connect app:

1. Go to: https://developers.kite.trade/apps/
2. Find your app (using your API key)
3. Add redirect URL: `http://localhost:8080/callback`
4. **Save** the settings

Without this step, the authentication flow will fail with an "Invalid redirect URI" error.

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

## Manual Method (Fallback)

If the automatic browser flow fails or you are on a headless server:

1. Run the legacy script:
   ```bash
   python3 get_kite_token.py
   ```
2. Follow the on-screen instructions to manually copy-paste the request token.

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
