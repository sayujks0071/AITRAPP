# Kite Trader CLI - Quick Start Guide

A simple command-line tool to login and start trading on Kite (Zerodha).

## Installation

1. **Install dependencies** (if not already installed):
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up your Kite API credentials** in `.env`:
   ```bash
   KITE_API_KEY=your_api_key_here
   KITE_API_SECRET=your_api_secret_here
   ```

   > Get your API credentials from: https://kite.trade/

## Usage

### Quick Start (Full Flow)

Login, select mode, and start trading in one command:

```bash
python kite_trader.py
```

This will:
1. ✅ Check if you're already logged in
2. 🔐 Guide you through login if needed
3. ⚙️  Let you select PAPER or LIVE mode
4. 🚀 Start the trading system

### Login Only

If you just want to login without starting the trading system:

```bash
python kite_trader.py --login-only
```

### Start with Specific Mode

Skip the mode selection prompt:

```bash
# Start in PAPER mode (safe, simulated trading)
python kite_trader.py --mode PAPER

# Start in LIVE mode (real money - requires confirmation)
python kite_trader.py --mode LIVE
```

### Check Status

View current session and configuration:

```bash
python kite_trader.py --status
```

### Setup Without Starting

Useful for CI/CD or automated setup:

```bash
python kite_trader.py --no-start --mode PAPER
```

## Login Process

When you run the tool for the first time:

1. **Get Login URL**: The tool generates a Kite login URL
2. **Open in Browser**: Visit the URL and login with your Zerodha credentials
3. **Get Request Token**: After login, you'll be redirected to a URL with a `request_token` parameter
4. **Paste Token**: Copy the `request_token` and paste it into the CLI
5. **Token Saved**: The access token is automatically saved to your `.env` file

### Example Login Flow

```
🔐 LOGIN TO KITE
======================================================================

📝 Login Steps:
1. Open this URL in your browser:

   https://kite.trade/connect/login?api_key=xxx&v=3

2. Login with your Zerodha credentials
3. After login, copy the 'request_token' from the redirect URL
   (URL will look like: http://...?request_token=XXXXX&...)

4. Paste the request_token here: [your_token_here]

🔄 Exchanging token...
✅ Login successful! Token saved to .env
```

## Trading Modes

### PAPER Mode (Recommended)
- ✅ **Safe**: No real money, simulated trades
- ✅ **Testing**: Perfect for testing strategies
- ✅ **Learning**: Learn without risk
- **Default mode**

### LIVE Mode (Warning!)
- ⚠️  **Real Money**: Executes actual trades
- ⚠️  **Risk**: You can lose money
- ⚠️  **Confirmation Required**: Must type "CONFIRM LIVE TRADING"
- ⚠️  **Production Use Only**

## API Endpoints

Once the trading system starts, you can access:

| Endpoint | Description |
|----------|-------------|
| `http://localhost:8000/health` | Health check |
| `http://localhost:8000/state` | System state & status |
| `http://localhost:8000/positions` | Current positions |
| `http://localhost:8000/orders` | Order history |
| `http://localhost:8000/risk` | Risk metrics |
| `http://localhost:8000/metrics` | Prometheus metrics |
| `http://localhost:8000/docs` | Interactive API docs |

## Control the Trading System

### Via API Endpoints

```bash
# Pause trading (stop taking new positions)
curl -X POST http://localhost:8000/pause

# Resume trading
curl -X POST http://localhost:8000/resume

# Kill switch (close all positions and pause)
curl -X POST http://localhost:8000/flatten

# Change mode (requires API key)
curl -X POST http://localhost:8000/mode \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_api_key" \
  -d '{"mode": "PAPER", "confirmation": "CONFIRM LIVE TRADING"}'
```

### Stopping the System

Press `Ctrl+C` in the terminal where the trading system is running.

## Troubleshooting

### "Session is invalid or expired"
**Solution**: Run the tool again. It will guide you through re-login.

### "ModuleNotFoundError"
**Solution**: Install dependencies:
```bash
pip install -r requirements.txt
```

### "Missing KITE_API_KEY"
**Solution**: Add your API credentials to `.env`:
```bash
KITE_API_KEY=your_key
KITE_API_SECRET=your_secret
```

### "Login failed"
**Solutions**:
- Make sure you copied the `request_token` correctly (it's the value after `request_token=` in the URL)
- Complete the login within 2-3 minutes (tokens expire quickly)
- Verify your API key and secret are correct
- Make sure you're logged in to the correct Zerodha account

### Request Token Expires Too Fast
**Tip**: Have the browser window and terminal side-by-side. As soon as you login and get redirected, immediately copy the `request_token` and paste it.

## Session Management

- **Token Validity**: Kite access tokens are valid for the trading day
- **Daily Login**: You need to login once per trading day
- **Auto-Save**: Tokens are automatically saved to `.env`
- **Session Check**: The tool automatically checks if your session is valid

## Security Notes

- 🔒 Never share your API key or secret
- 🔒 Never commit `.env` file to git (already in `.gitignore`)
- 🔒 Keep your `request_token` and `access_token` private
- 🔒 Use PAPER mode for testing and development
- 🔒 Only use LIVE mode on production systems with proper monitoring

## Advanced Usage

### Custom Port

Change the API port in `.env`:
```bash
API_PORT=8080
```

### Enable Auto-Reload (Development)

For development, enable auto-reload in `.env`:
```bash
RELOAD=true
```

### Use with Existing Scripts

The tool integrates with existing scripts:

```bash
# After login with kite_trader.py, use other tools:
python scripts/paper_e2e.py           # Run end-to-end test
python scripts/run_backtest.py        # Run backtest
```

## Daily Workflow

### Morning (Before Market Opens)

```bash
# 1. Login and start in PAPER mode
python kite_trader.py --mode PAPER

# 2. Check status via API
curl http://localhost:8000/health
curl http://localhost:8000/state
```

### During Trading Hours

Monitor positions and risk:
```bash
# View positions
curl http://localhost:8000/positions

# Check risk metrics
curl http://localhost:8000/risk

# View system state
curl http://localhost:8000/state
```

### End of Day

```bash
# Flatten all positions
curl -X POST http://localhost:8000/flatten

# Stop system
# Press Ctrl+C in the trading system terminal
```

## Alternative Login Methods

### Method 1: Using `kite_trader.py` (Recommended)
```bash
python kite_trader.py --login-only
```

### Method 2: Using `get_kite_token.py`
```bash
python get_kite_token.py
```

### Method 3: Using Bootstrap Script
```bash
python scripts/kite_auth_bootstrap.py
```

### Method 4: Via API Callback
Start the API server first, then complete OAuth flow via browser callback.

## Example Session

```bash
$ python kite_trader.py

======================================================================
    🚀 AITRAPP - Kite Trading System
======================================================================

📡 Checking session status...
❌ Session is invalid or expired

⚠️  You need to login first

======================================================================
    🔐 LOGIN TO KITE
======================================================================

📝 Login Steps:
1. Open this URL in your browser:
   https://kite.trade/connect/login?api_key=xxx&v=3
...
✅ Login successful! Token saved to .env

======================================================================
    ⚙️  SELECT TRADING MODE
======================================================================

Current mode: PAPER

Available modes:
  1. PAPER  - Simulated trading (safe, no real money)
  2. LIVE   - Real trading (WARNING: uses real money!)

Select mode (1 for PAPER, 2 for LIVE) [1]: 1
✅ Updated APP_MODE to PAPER in .env

======================================================================
    🚀 STARTING TRADING SYSTEM
======================================================================

Mode: PAPER
Port: 8000

Starting API server...

API endpoints will be available at:
  - Health:     http://localhost:8000/health
  - Status:     http://localhost:8000/state
  - Positions:  http://localhost:8000/positions
  - Risk:       http://localhost:8000/risk
  - Metrics:    http://localhost:8000/metrics
  - API Docs:   http://localhost:8000/docs

======================================================================
Press Ctrl+C to stop the trading system
======================================================================

INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

## Getting Help

```bash
python kite_trader.py --help
```

For more information:
- **Authentication Guide**: See `docs/auth.md`
- **API Documentation**: Visit `http://localhost:8000/docs` after starting
- **Issues**: Report at https://github.com/sayujks0071/AITRAPP/issues

---

**Happy Trading!** 🚀📈
