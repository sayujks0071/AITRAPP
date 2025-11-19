# 🔄 Kite Access Token Refresh - Day-4

## ⚠️ Current Status

**Your Kite access token is EXPIRED** and needs to be refreshed before Day-4 trading.

**Token Expiry:** Kite access tokens expire daily at **midnight IST** (00:00 IST).

---

## 🚀 Quick Refresh Steps

### Option 1: Using the Helper Script (Recommended)

1. **Open the Kite login page** (already opened in browser):
   ```
   https://kite.trade/connect/login?api_key=nhe2vo0afks02ojs&v=3
   ```

2. **Login with your Zerodha credentials:**
   - Enter your Kite username and password
   - Complete 2FA if prompted

3. **Get the request_token from the callback URL:**
   - After login, you'll be redirected to a URL like:
     ```
     http://localhost:8080/callback?request_token=XXXXX&action=login&status=success
     ```
   - **Copy the `request_token` value** (the part after `request_token=`)

4. **Run the refresh script:**
   ```bash
   cd /Users/mac/CRYPTO/AITRAPP
   export $(grep -v '^#' .env | xargs)
   python3 scripts/kite_token_refresh.py --request-token YOUR_REQUEST_TOKEN
   ```

   **Example:**
   ```bash
   python3 scripts/kite_token_refresh.py --request-token abc123xyz456
   ```

5. **The script will:**
   - Generate a new access token
   - Automatically update your `.env` file
   - Show you the export command to use

6. **Restart the API** (if it's running):
   ```bash
   # Stop current API
   pkill -f "uvicorn apps.api.main:app"
   
   # Restart with fresh token
   export APP_MODE=LIVE
   export APP_CONFIG=configs/kite_day1_live.yaml
   export $(grep -v '^#' .env | xargs)
   python3 -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8000
   ```

---

### Option 2: Manual Update

If you prefer to do it manually:

1. **Get the request_token** (same as Option 1, steps 1-3)

2. **Generate access token manually:**
   ```python
   from kiteconnect import KiteConnect
   
   api_key = "nhe2vo0afks02ojs"
   api_secret = "cs82nkkdvin37nrydnyou6cwn2b8zojl"
   request_token = "YOUR_REQUEST_TOKEN"
   
   kite = KiteConnect(api_key=api_key)
   data = kite.generate_session(request_token, api_secret=api_secret)
   
   print(f"Access Token: {data['access_token']}")
   print(f"User ID: {data['user_id']}")
   ```

3. **Update `.env` file:**
   ```bash
   # Edit .env file
   nano .env
   
   # Update this line:
   KITE_ACCESS_TOKEN=your_new_access_token_here
   ```

4. **Restart the API** (same as Option 1, step 6)

---

## ✅ Verify Token is Valid

After refreshing, verify the token works:

```bash
cd /Users/mac/CRYPTO/AITRAPP
export $(grep -v '^#' .env | xargs)
python3 scripts/kite_token_check.py
```

**Expected output:**
```
============================================================
✅ Token is valid and working!
============================================================

📋 User ID: YOUR_USER_ID
📋 API Key: nhe2vo0afks02...
📋 Token: abc123xyz456...

✅ Ready for LIVE trading!
============================================================
```

---

## 📋 Your Kite Credentials

- **API Key:** `nhe2vo0afks02ojs`
- **API Secret:** `cs82nkkdvin37nrydnyou6cwn2b8zojl`
- **Login URL:** `https://kite.trade/connect/login?api_key=nhe2vo0afks02ojs&v=3`

---

## ⏰ Daily Routine

Since tokens expire daily at midnight IST, your **morning routine** should include:

1. **Before market open (8:55 AM IST):**
   - Refresh the token using the steps above
   - Verify token is valid
   - Restart API if needed

2. **Or automate it:**
   - Set up a daily cron job to remind you
   - Or use a scheduled task to run the refresh script

---

## 🔒 Security Notes

- ✅ **Never commit tokens to git** (`.env` is already in `.gitignore`)
- ✅ **Tokens expire daily** - this is a security feature
- ✅ **Request tokens expire quickly** - use within a few minutes
- ✅ **Access tokens are session-specific** - each login generates a new one

---

## 🐛 Troubleshooting

### "Token is invalid or expired"
- ✅ **Solution:** Run the refresh script (tokens expire daily)
- ✅ **Check:** Make sure you're using the token from today

### "Request token expired"
- ✅ **Solution:** Get a fresh request_token by logging in again
- ✅ **Note:** Request tokens expire within minutes, use immediately

### "Connection refused" on callback URL
- ✅ **This is normal!** You just need the `request_token` from the URL
- ✅ The callback URL doesn't need to work - it's just for getting the token

### "Invalid API key"
- ✅ **Check:** Verify API key is correct: `nhe2vo0afks02ojs`
- ✅ **Check:** Ensure API key is active in Kite Connect dashboard

---

## 📞 Quick Reference

**Refresh Command:**
```bash
python3 scripts/kite_token_refresh.py --request-token YOUR_TOKEN
```

**Check Command:**
```bash
python3 scripts/kite_token_check.py
```

**Makefile Shortcuts:**
```bash
make kite-token-refresh  # Refresh token (opens browser)
make kite-token-check    # Verify token is valid
```

---

**Last Updated:** 2025-11-19  
**Status:** Token needs refresh before Day-4 trading

