# Kite Daily Auth Assistant

Purpose: bootstrap the Zerodha Kite session each morning without automating credentials.

## What it does

- Enforces manual login (no credential automation).
- Starts a local callback server to capture `request_token`.
- Exchanges `request_token` -> `access_token`.
- Persists `KITE_ACCESS_TOKEN`, `KITE_USER_ID`, and `KITE_TOKEN_CREATED_AT_ISO` in `.env` without printing the token.
- Warns when `TRADING_MODE`/`APP_MODE` is missing (defaults to `PAPER`), and permits `LIVE` execution if configured.

## Prerequisites

- `KITE_API_KEY` and `KITE_API_SECRET` present in `.env`.
- Kite Connect app redirect URL set to `http://127.0.0.1:8080/callback` (or your custom host/port).
- Python env with `kiteconnect` installed.

## Usage (daily at 08:00 IST)

```bash
python3 scripts/kite_auth_bootstrap.py
```

The script opens the login URL in your browser. Log in manually, complete 2FA, and the token exchange will happen automatically after the redirect.

## Configuration (optional)

- `KITE_ENV_FILE` (default: `.env`)
- `KITE_AUTH_HOST` (default: `127.0.0.1`)
- `KITE_AUTH_PORT` (default: `8080`)
- `KITE_AUTH_TIMEOUT_SEC` (default: `180`)

## Troubleshooting

- Port already in use: change `KITE_AUTH_PORT`.
- Missing `request_token`: confirm the Kite app redirect URL matches the host/port.
- Token exchange fails: the `request_token` may have expired; log in again and retry.

## Security Notes

- Tokens expire daily; rerun before market open.
- `.env` is git-ignored; do not copy tokens into source control.
- The assistant never prints the access token to stdout.
