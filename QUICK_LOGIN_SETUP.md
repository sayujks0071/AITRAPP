# 🚀 Quick Login & Test Setup

## Current Status

✅ **Done:**
- `.env` file created with your API credentials
- PostgreSQL is running
- Redis is being set up

⚠️ **Need to do:**
1. Get Kite Access Token (Automated!)
2. Install Python 3.11+ (or use existing)
3. Install dependencies
4. Run database migrations
5. Start the app

---

## Step 1: Get Kite Access Token

**Recommended Method: Automated Bootstrap**

We have a new automated script that opens the browser, captures the token, and updates your `.env` file automatically.

1. Run the bootstrap script:
   ```bash
   python3 scripts/kite_auth_bootstrap.py
   ```
   *Follow the browser prompt to login.*

2. That's it! Your `.env` file is now updated.

**Legacy Method (Manual):**

If the script fails, refer to `GET_KITE_TOKEN.md` for the manual copy-paste method.

### Option B: Using MCP Server (If Already Authenticated)

If you've already authenticated with the MCP server, you might have the token stored. Check:

```bash
cat kite-mcp-server/.env | grep ACCESS_TOKEN
```

---

## Step 2: Update .env File

*Skipped if you used the bootstrap script above!*

Otherwise, edit `.env` and add your access token and user ID manually.

---

## Step 3: Setup Python Environment

```bash
cd /Users/mac/AITRAPP

# Use Python 3.11 if available, otherwise install it
eval "$(/opt/homebrew/bin/brew shellenv)"
python3.11 -m venv venv  # or python3 if 3.11+ is default

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

---

## Step 4: Setup Database

```bash
# Make sure PostgreSQL is running
eval "$(/opt/homebrew/bin/brew shellenv)"
brew services start postgresql@16

# Create database if it doesn't exist
createdb aitrapp 2>/dev/null || echo "Database might already exist"

# Run migrations
alembic upgrade head
```

---

## Step 5: Start the App

```bash
# Make sure Redis is running
brew services start redis

# Start in PAPER mode (safe testing)
make paper

# Or start directly:
source venv/bin/activate
export APP_MODE=PAPER
python -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## Step 6: Test the App

In a new terminal:

```bash
# Check health
curl http://localhost:8000/health | jq

# Check system state
curl http://localhost:8000/state | jq

# View positions (should be empty)
curl http://localhost:8000/positions | jq

# View metrics
curl http://localhost:8000/metrics
```

---

## Troubleshooting

### Python Version Issue
If you get errors about Python version:
```bash
# Install Python 3.11
brew install python@3.11

# Use it explicitly
/opt/homebrew/opt/python@3.11/bin/python3.11 -m venv venv
```

### Database Connection Error
```bash
# Check PostgreSQL is running
brew services list | grep postgresql

# Check connection
psql -h localhost -U trader -d aitrapp
```

### Redis Connection Error
```bash
# Start Redis
brew services start redis

# Test connection
redis-cli ping
```

---

## Next Steps

Once the app is running:
1. Monitor logs: `tail -f logs/aitrapp.log | jq`
2. Check dashboard: Open http://localhost:3000 (if web app is running)
3. Test strategies in PAPER mode
4. Review `LAUNCH_CARD.md` before going LIVE

---

**Need help?** Check:
- `FAST_FAQ.md` - Quick diagnostics
- `QUICKSTART.md` - Detailed setup guide
- `README.md` - Full documentation
