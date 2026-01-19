# 🚀 START HERE - Login & Test Your App

## ✅ What's Already Done

- ✅ `.env` file created with your API credentials
- ✅ Python 3.11 virtual environment set up
- ✅ PostgreSQL database created
- ✅ Redis is running
- ✅ Core dependencies installed
- ✅ Token generator script ready

## 🎯 Next Steps (5 minutes)

### Step 1: Get Your Kite Access Token

You need to authenticate with Kite Connect to get an access token.

**Option A: Use the helper script (Recommended)**
```bash
cd /Users/mac/AITRAPP
source venv/bin/activate
python scripts/kite_auth_bootstrap.py
```

The script will:
1. Check if your current session is valid
2. If invalid, start a local server to capture the token
3. Show you the login URL
4. Automatically update your `.env` file after callback

**Option B: Manual process**
1. Visit the login URL provided by the script
2. Login with your Zerodha credentials
3. Copy the `request_token` from the redirect URL
4. Run: `python scripts/kite_auth_bootstrap.py YOUR_REQUEST_TOKEN`

### Step 2: Update .env File

If you didn't use the auto-update option, edit `.env`:
```bash
nano .env
```

Update these lines:
```
KITE_ACCESS_TOKEN=your_actual_access_token_here
KITE_USER_ID=your_actual_user_id_here
```

### Step 3: Install Remaining Dependencies

```bash
cd /Users/mac/AITRAPP
source venv/bin/activate
pip install -r requirements.txt
```

(Some packages might have warnings, but core functionality should work)

### Step 4: Run Database Migrations

```bash
# Make sure PostgreSQL bin is in PATH
eval "$(/opt/homebrew/bin/brew shellenv)"
export PATH="/opt/homebrew/opt/postgresql@16/bin:$PATH"

# Run migrations
alembic upgrade head
```

### Step 5: Start the App

```bash
cd /Users/mac/AITRAPP
source venv/bin/activate

# Start in PAPER mode (safe testing)
make paper

# Or start directly:
export APP_MODE=PAPER
python -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 --reload
```

### Step 6: Test the App

Open a **new terminal** and run:

```bash
# Check health
curl http://localhost:8000/health | jq

# Check system state
curl http://localhost:8000/state | jq

# View positions (should be empty initially)
curl http://localhost:8000/positions | jq

# View metrics
curl http://localhost:8000/metrics | head -20
```

---

## 🆘 Troubleshooting

### "Access token expired" or "Invalid token"
- Access tokens expire daily
- Re-run `python scripts/kite_auth_bootstrap.py` to get a new token

### "Database connection error"
```bash
# Check PostgreSQL is running
eval "$(/opt/homebrew/bin/brew shellenv)"
brew services list | grep postgresql

# Start if needed
brew services start postgresql@16
```

### "Redis connection error"
```bash
# Check Redis is running
redis-cli ping  # Should return PONG

# Start if needed
brew services start redis
```

### "Module not found" errors
```bash
source venv/bin/activate
pip install -r requirements.txt
```

---

## 📚 Quick Reference

- **Get token**: `python scripts/kite_auth_bootstrap.py`
- **Start app**: `make paper`
- **Check health**: `curl http://localhost:8000/health | jq`
- **View logs**: `tail -f logs/aitrapp.log | jq`
- **Stop app**: `Ctrl+C` in the terminal running the app

---

## 🎉 You're Ready!

Once the app is running:
1. Monitor the logs for any errors
2. Check the `/state` endpoint to see system status
3. Test in PAPER mode before going LIVE
4. Review `LAUNCH_CARD.md` before switching to LIVE mode

**Need help?** Check:
- `QUICK_LOGIN_SETUP.md` - Detailed setup guide
- `FAST_FAQ.md` - Quick diagnostics
- `README.md` - Full documentation

