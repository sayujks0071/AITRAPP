# 🌅 Morning Login Guide - Express & Automated

## Quick Start

### One-Click Morning Login

```bash
# Express login (opens browser, auto-updates token)
bash scripts/morning_startup.sh

# Express login + auto-start API
bash scripts/morning_startup.sh --start-api
```

That's it! The script will:
1. ✅ Check if token is valid
2. ✅ Refresh token if needed (opens browser for quick login)
3. ✅ Clean up old tokens/logs
4. ✅ Verify environment
5. ✅ Verify Kite connection
6. ✅ Optionally start API

---

## Express Login (Manual)

If you just want to refresh the token:

```bash
python3 scripts/kite_express_login.py
```

**What it does:**
- Opens browser for Kite login
- Waits for you to paste request_token
- Automatically updates `.env` file
- Shows export command

**With auto-restart:**
```bash
python3 scripts/kite_express_login.py --auto-restart
```

---

## Automatic Token Refresh

### Check Token Validity

```bash
# Check if token needs refresh
python3 scripts/kite_auto_refresh.py --check
```

### Background Daemon

```bash
# Run as background service (checks every hour)
python3 scripts/kite_auto_refresh.py --daemon
```

### Scheduled Refresh

Add to crontab for daily refresh at 8:55 AM IST:

```bash
# Edit crontab
crontab -e

# Add this line (runs daily at 8:55 AM IST)
55 8 * * 1-5 cd /Users/mac/CRYPTO/AITRAPP && /usr/bin/python3 scripts/kite_express_login.py --request-token $(curl -s "https://kite.trade/connect/login?api_key=YOUR_API_KEY&v=3" | grep -oP 'request_token=\K[^&]+') || bash scripts/morning_startup.sh
```

**Note:** The scheduled refresh requires manual login (Kite doesn't support fully automated OAuth).

---

## Token Cleanup

Old tokens are automatically cleaned up during:
- Express login
- Morning startup
- Token refresh

**Manual cleanup:**
```bash
# Clean up old token backups/logs
python3 scripts/kite_express_login.py  # Includes cleanup
```

---

## Integration with API

The API can automatically detect token expiry and prompt for refresh:

```python
# In packages/core/kite_client.py
# Token refresh callback is already implemented
# Just needs to be wired to express login script
```

**Future enhancement:** API can auto-trigger express login on token expiry.

---

## Daily Routine

### Option 1: Manual (Recommended for now)

```bash
# Morning (8:55 AM IST)
bash scripts/morning_startup.sh --start-api

# That's it! System is ready.
```

### Option 2: Scheduled (Future)

1. Set up cron job for morning startup
2. Manual login still required (Kite OAuth)
3. System auto-starts after login

---

## Troubleshooting

### "Token needs refresh" but express login fails

1. **Check browser opened:**
   ```bash
   python3 scripts/kite_express_login.py
   # Manually open: https://kite.trade/connect/login?api_key=YOUR_API_KEY&v=3
   ```

2. **Verify credentials:**
   ```bash
   echo $KITE_API_KEY
   echo $KITE_API_SECRET
   ```

3. **Manual refresh:**
   ```bash
   python3 scripts/kite_token_refresh.py --interactive
   ```

### API not starting after token refresh

```bash
# Check if API process exists
ps aux | grep uvicorn

# Check logs
tail -f /tmp/uvicorn_morning_startup.log

# Manual start
export APP_MODE=LIVE
export APP_CONFIG=configs/kite_day1_live.yaml
export $(grep -v '^#' .env | xargs)
python3 -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8000
```

### Token refresh timestamp not updating

The `.env` file should have:
```
KITE_TOKEN_REFRESHED_AT=2025-11-19T09:00:00.123456
```

If missing, express login will add it automatically.

---

## Security Notes

- ✅ Tokens are stored in `.env` (already in `.gitignore`)
- ✅ Token refresh timestamp tracked for age checking
- ✅ Old tokens automatically cleaned up
- ✅ No tokens logged to console (only first 20 chars shown)

---

## Files Created

1. **`scripts/kite_express_login.py`** - One-click express login
2. **`scripts/kite_auto_refresh.py`** - Auto token refresh daemon
3. **`scripts/morning_startup.sh`** - Complete morning routine
4. **`MORNING_LOGIN_GUIDE.md`** - This guide

---

## Quick Reference

| Command | Purpose |
|---------|---------|
| `bash scripts/morning_startup.sh` | Complete morning routine |
| `python3 scripts/kite_express_login.py` | Express login only |
| `python3 scripts/kite_auto_refresh.py --check` | Check token validity |
| `python3 scripts/kite_token_check.py` | Verify token works |

---

**Last Updated:** 2025-11-19  
**Status:** Ready for use

