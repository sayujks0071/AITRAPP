# Kite Authentication Guide

This system uses Zerodha Kite Connect for trading. Kite Connect requires a mandatory manual login once every 24 hours to generate a new `access_token`.

## Daily Authentication Flow (8:00 AM IST)

We use a "Bootstrap" approach to handle authentication separately from the trading logic.

1.  **Check Session**: The system checks if the current `access_token` in `.env` is valid.
2.  **Manual Login**: If invalid/expired, it prompts for a manual login via the Kite web interface.
3.  **Token Exchange**: After login, the system captures the `request_token` via a local callback server, exchanges it for an `access_token`, and updates `.env`.
4.  **Secure Storage**: The token is stored locally in `.env`.

## Usage

### Manual (Development/Local)

Run the bootstrap script:

```bash
python scripts/kite_auth_bootstrap.py
```

Follow the on-screen instructions:
1.  Open the provided URL.
2.  Login to Zerodha.
3.  The script will automatically capture the token and exit.

### Automated Scheduler (Production/VPS)

Add a cron job to run at 8:00 AM IST (02:30 UTC):

```bash
# Open crontab
crontab -e

# Add entry (Times are in server local time, adjust accordingly)
# Example for UTC server (02:30 UTC = 08:00 IST)
30 2 * * * cd /path/to/repo && /usr/bin/python3 scripts/kite_auth_bootstrap.py >> /var/log/kite_auth.log 2>&1
```

**Note:** Since this requires manual interaction (login), this cron job is useful to *start* the process and log the URL. You must still click the link and login.

Alternatively, if you have a headless server, you can use SSH port forwarding to access the localhost callback:

`ssh -L 8080:localhost:8080 user@server`

Then clicking the link on your local machine will redirect to `localhost:8080` which is forwarded to the server.

## Security

*   **No Automated Login**: We strictly follow Kite Trade guidelines and do not automate the login page.
*   **No Secrets in Logs**: Tokens are masked in logs.
*   **Live Trading Protection**: `TRADING_MODE` defaults to `PAPER` unless explicitly overridden.

## Troubleshooting

*   **Port 8080 in use**: The script tries to bind to port 8080. Ensure it's free.
*   **Token Invalid**: If the script says "Session valid" but trading fails, delete the `KITE_ACCESS_TOKEN` line from `.env` and run the script again.
