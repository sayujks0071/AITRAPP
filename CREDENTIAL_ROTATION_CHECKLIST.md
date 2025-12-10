# 🔄 Credential Rotation Checklist

## 🚨 CRITICAL: Credentials Exposed in `.env.bak`

**All credentials in `.env.bak` are compromised and MUST be rotated immediately.**

---

## ✅ Immediate Actions (Do Now)

### 1. Kite Connect API Credentials

**Current (COMPROMISED):**
- API Key: `nhe2vo0afks02ojs`
- API Secret: `cs82nkkdvin37nrydnyou6cwn2b8zojl`
- Access Token: `iyYyjjA0q8xfsYPqUt25MfxS0o32vN0m`
- User ID: `MM2076`

**Steps:**
1. [ ] Login to [Zerodha Kite Connect](https://kite.trade/apps/)
2. [ ] Go to "API Management"
3. [ ] Find API key: `nhe2vo0afks02ojs`
4. [ ] Click "Revoke" or "Delete"
5. [ ] Generate new API key
6. [ ] Copy new API key and secret
7. [ ] Update `.env` file:
   ```bash
   KITE_API_KEY=<new_key>
   KITE_API_SECRET=<new_secret>
   ```
8. [ ] Generate new access token using new credentials
9. [ ] Update `.env` file:
   ```bash
   KITE_ACCESS_TOKEN=<new_token>
   KITE_USER_ID=<user_id>
   ```
10. [ ] Test new credentials: `python3 scripts/kite_token_check.py`

---

### 2. Telegram Bot Token

**Current (COMPROMISED):**
- Bot Token: `8101314149:AAHDrcayh3-ZSM2xJLwYhiYgfA-44toVZX8`

**Steps:**
1. [ ] Open Telegram
2. [ ] Message [@BotFather](https://t.me/BotFather)
3. [ ] Send: `/revoke`
4. [ ] Select your bot from the list
5. [ ] Confirm revocation
6. [ ] Generate new token: `/newtoken`
7. [ ] Select your bot
8. [ ] Copy new token
9. [ ] Update `.env` file:
   ```bash
   TELEGRAM_BOT_TOKEN=<new_token>
   ```
10. [ ] Test bot: `python3 scripts/test_telegram_bot.py`

---

### 3. Database Credentials

**Steps:**
1. [ ] Connect to PostgreSQL as superuser
2. [ ] Change password for database user:
   ```sql
   ALTER USER aitrapp WITH PASSWORD '<new_strong_password>';
   ```
3. [ ] Update `.env` file:
   ```bash
   DATABASE_URL=postgresql://aitrapp:<new_password>@localhost:5432/aitrapp
   ```
4. [ ] Test connection: `python3 scripts/verify_env.py`
5. [ ] Restart API server

---

### 4. API Secret Key

**Steps:**
1. [ ] Generate new secret key (min 32 characters):
   ```bash
   python3 -c "import secrets; print(secrets.token_urlsafe(32))"
   ```
2. [ ] Update `.env` file:
   ```bash
   API_SECRET_KEY=<new_secret_key>
   ```
3. [ ] Restart API server

---

### 5. Cleanup

**Steps:**
1. [ ] Delete `.env.bak` file:
   ```bash
   rm .env.bak
   ```
2. [ ] Verify `.gitignore` includes `.env.bak` (already done)
3. [ ] Commit the removal:
   ```bash
   git add .gitignore
   git commit -m "security: remove .env.bak and add to gitignore"
   ```

---

## 🧪 Verification Steps

After rotation, verify everything works:

1. [ ] **Kite Connection:**
   ```bash
   python3 scripts/kite_token_check.py
   ```
   Should show: ✅ Token valid

2. [ ] **Telegram Bot:**
   ```bash
   python3 scripts/test_telegram_bot.py
   ```
   Should send test message

3. [ ] **Database:**
   ```bash
   python3 scripts/verify_env.py
   ```
   Should show: ✅ Database connection OK

4. [ ] **API Server:**
   ```bash
   curl http://localhost:8000/health
   ```
   Should return: `{"status": "ok", "mode": "LIVE"}`

---

## 📋 Post-Rotation Checklist

- [ ] All credentials rotated
- [ ] All services tested
- [ ] `.env.bak` deleted
- [ ] Git commit made (removing `.env.bak`)
- [ ] Monitor accounts for suspicious activity
- [ ] Review git history (if private repo, consider force-push to remove history)

---

## ⚠️ Important Notes

1. **Do NOT** use old credentials after rotation
2. **Monitor** Kite account for unauthorized trades
3. **Check** Telegram bot for unauthorized messages
4. **Review** database logs for suspicious access
5. **Consider** enabling 2FA on Kite account if not already enabled

---

## 🔍 If Repository is Public

If this repository is public or shared:

1. **Consider** making repository private
2. **Review** git history - credentials may be in commit history
3. **Consider** using `git filter-branch` or BFG Repo-Cleaner to remove from history
4. **Rotate** credentials even if you make repo private (they're already exposed)

---

**Status:** 🔴 **URGENT - Complete rotation within 24 hours**

*This checklist should be completed immediately to secure your system.*






## 🚨 CRITICAL: Credentials Exposed in `.env.bak`

**All credentials in `.env.bak` are compromised and MUST be rotated immediately.**

---

## ✅ Immediate Actions (Do Now)

### 1. Kite Connect API Credentials

**Current (COMPROMISED):**
- API Key: `nhe2vo0afks02ojs`
- API Secret: `cs82nkkdvin37nrydnyou6cwn2b8zojl`
- Access Token: `iyYyjjA0q8xfsYPqUt25MfxS0o32vN0m`
- User ID: `MM2076`

**Steps:**
1. [ ] Login to [Zerodha Kite Connect](https://kite.trade/apps/)
2. [ ] Go to "API Management"
3. [ ] Find API key: `nhe2vo0afks02ojs`
4. [ ] Click "Revoke" or "Delete"
5. [ ] Generate new API key
6. [ ] Copy new API key and secret
7. [ ] Update `.env` file:
   ```bash
   KITE_API_KEY=<new_key>
   KITE_API_SECRET=<new_secret>
   ```
8. [ ] Generate new access token using new credentials
9. [ ] Update `.env` file:
   ```bash
   KITE_ACCESS_TOKEN=<new_token>
   KITE_USER_ID=<user_id>
   ```
10. [ ] Test new credentials: `python3 scripts/kite_token_check.py`

---

### 2. Telegram Bot Token

**Current (COMPROMISED):**
- Bot Token: `8101314149:AAHDrcayh3-ZSM2xJLwYhiYgfA-44toVZX8`

**Steps:**
1. [ ] Open Telegram
2. [ ] Message [@BotFather](https://t.me/BotFather)
3. [ ] Send: `/revoke`
4. [ ] Select your bot from the list
5. [ ] Confirm revocation
6. [ ] Generate new token: `/newtoken`
7. [ ] Select your bot
8. [ ] Copy new token
9. [ ] Update `.env` file:
   ```bash
   TELEGRAM_BOT_TOKEN=<new_token>
   ```
10. [ ] Test bot: `python3 scripts/test_telegram_bot.py`

---

### 3. Database Credentials

**Steps:**
1. [ ] Connect to PostgreSQL as superuser
2. [ ] Change password for database user:
   ```sql
   ALTER USER aitrapp WITH PASSWORD '<new_strong_password>';
   ```
3. [ ] Update `.env` file:
   ```bash
   DATABASE_URL=postgresql://aitrapp:<new_password>@localhost:5432/aitrapp
   ```
4. [ ] Test connection: `python3 scripts/verify_env.py`
5. [ ] Restart API server

---

### 4. API Secret Key

**Steps:**
1. [ ] Generate new secret key (min 32 characters):
   ```bash
   python3 -c "import secrets; print(secrets.token_urlsafe(32))"
   ```
2. [ ] Update `.env` file:
   ```bash
   API_SECRET_KEY=<new_secret_key>
   ```
3. [ ] Restart API server

---

### 5. Cleanup

**Steps:**
1. [ ] Delete `.env.bak` file:
   ```bash
   rm .env.bak
   ```
2. [ ] Verify `.gitignore` includes `.env.bak` (already done)
3. [ ] Commit the removal:
   ```bash
   git add .gitignore
   git commit -m "security: remove .env.bak and add to gitignore"
   ```

---

## 🧪 Verification Steps

After rotation, verify everything works:

1. [ ] **Kite Connection:**
   ```bash
   python3 scripts/kite_token_check.py
   ```
   Should show: ✅ Token valid

2. [ ] **Telegram Bot:**
   ```bash
   python3 scripts/test_telegram_bot.py
   ```
   Should send test message

3. [ ] **Database:**
   ```bash
   python3 scripts/verify_env.py
   ```
   Should show: ✅ Database connection OK

4. [ ] **API Server:**
   ```bash
   curl http://localhost:8000/health
   ```
   Should return: `{"status": "ok", "mode": "LIVE"}`

---

## 📋 Post-Rotation Checklist

- [ ] All credentials rotated
- [ ] All services tested
- [ ] `.env.bak` deleted
- [ ] Git commit made (removing `.env.bak`)
- [ ] Monitor accounts for suspicious activity
- [ ] Review git history (if private repo, consider force-push to remove history)

---

## ⚠️ Important Notes

1. **Do NOT** use old credentials after rotation
2. **Monitor** Kite account for unauthorized trades
3. **Check** Telegram bot for unauthorized messages
4. **Review** database logs for suspicious access
5. **Consider** enabling 2FA on Kite account if not already enabled

---

## 🔍 If Repository is Public

If this repository is public or shared:

1. **Consider** making repository private
2. **Review** git history - credentials may be in commit history
3. **Consider** using `git filter-branch` or BFG Repo-Cleaner to remove from history
4. **Rotate** credentials even if you make repo private (they're already exposed)

---

**Status:** 🔴 **URGENT - Complete rotation within 24 hours**

*This checklist should be completed immediately to secure your system.*







