# Kite Day-1 LIVE Canary — Launch Checklist

**Date:** Tomorrow | **Capital:** ₹20-50k | **Risk:** 0.30% per trade | **Daily Cap:** -1.50%

---

## ⏰ 08:55 IST — Pre-Open Setup

### Step 1: Fresh Token (30 seconds)
```bash
export KITE_API_KEY="****"
export KITE_API_SECRET="****"
make kite-token-refresh

# Copy and paste the two export lines it prints:
export KITE_ACCESS_TOKEN="***"
export KITE_USER_ID="***"
```

### Step 2: Environment + Gate
```bash
export APP_MODE=LIVE
export APP_TIMEZONE=Asia/Kolkata
export EXPECTED_EGRESS_IP="x.x.x.x"   # must match your broker allowlist

make prelive-gate                     # Should PASS
```

**✅ Gate checks:**
- Egress IP matches allowlist
- Day-2 JSON fresh + PASS
- Heartbeats < 5s
- Leader lock available

---

## ⏰ 09:00 IST — Launch Monitor

```bash
make kite-canary-launch               # starts monitor; shows /metrics watch
```

**In another terminal tab:**
```bash
make kite-canary-status              # quick health snapshot
```

---

## ⏰ 09:15 IST — Position Sizing

```bash
# Example: ₹30k capital, 0.30% risk per trade
make kite-size CAPITAL=30000 RISK_PCT=0.30

# Use the output to pick debit spread width/price
```

**Expected outputs:**
- ₹20k → risk ₹60 → net debit ≈ ₹2.40/lot
- ₹30k → risk ₹90 → net debit ≈ ₹3.60/lot
- ₹50k → risk ₹150 → net debit ≈ ₹6.00/lot

---

## ⏰ 09:30-10:30 IST — Entry Window

**Strategy:** NIFTY weekly debit spread only (one attempt, no re-entries)

**Risk caps (canary):**
- 0.30% per trade
- 1.0% portfolio heat
- -1.50% daily stop
- 1-2 positions max

**Entry guards:**
- ORB(15) bias + trend filter
- Spread ≤ 0.5% of mid
- OI ≥ 50k, Volume ≥ 100
- Not in F&O ban

**Exits:**
- Stop: -50% of net debit
- TP: +60-80% of net debit
- Timeout: Exit by 15:10-15:20 if still open
- **Hard flat: 15:25 IST** (system enforced)

---

## 📊 What "Good" Looks Like (Watch Pane)

**Healthy metrics:**
- `trader_is_leader = 1`
- Heartbeats `< 5s` (marketdata / order_stream / scan)
- `trader_scan_ticks_total` rising steadily
- `trader_leader_changes_total = 0`
- `trader_oco_orphans_total = 0`

**Watch commands:**
```bash
make watch-metrics    # Equity (Kite) metrics
make watch-all        # Unified (all metrics)
```

---

## 🛑 Fast Controls (Keep Handy)

### Status Check
```bash
make kite-canary-status
```

### Emergency Flatten
```bash
curl -s -X POST :8000/flatten | jq
```

### Stop & Flatten
```bash
make kite-canary-stop     # flattens and stops API
```

---

## ⏰ 15:25+ IST — Post-Close

```bash
make kite-canary-stop

make burnin-report && make reconcile-db && make post-close

make score-day2
```

**Capture:**
- Screenshots (fills, P&L, latency)
- Export logs/artifacts
- Note slippage vs quoted mid
- Note spread behavior at entry/exit

---

## ⚠️ Troubleshooting

### If `prelive-gate` blocks on egress IP:
- Set `EXPECTED_EGRESS_IP` to your broker-allowlisted public IP
- Rerun: `make prelive-gate`

### If any gauge drifts:
- **Leader flips** (`trader_is_leader` → 0)
- **Heartbeats ≥ 5s**
- **OCO orphans > 0**

**Action:**
1. Pause entries immediately
2. If unresolved in 2-3 minutes: `make kite-canary-stop`
3. Diagnose issue
4. Relaunch after fix

### If token refresh fails:
- **"Request token expired"** → Use token within a few minutes of login
- **"Invalid token"** → Token expires daily at midnight IST - refresh each morning
- **"Redirect URI mismatch"** → Check Kite Connect app settings

**Fix:** Restart OAuth flow: `make kite-token-refresh`

---

## 🔒 Security Notes

- ✅ `.env` is in `.gitignore` (secrets safe)
- ⚠️ Don't paste keys in chat or commit them
- 💡 Consider `trap 'unset KITE_ACCESS_TOKEN' EXIT` for auto-cleanup
- 💡 Keep NTP synced (clock drift can cause token failures)

---

## 📋 Quick Reference

| Command | Purpose |
|---------|---------|
| `make kite-token-refresh` | Get fresh access token (daily) |
| `make kite-token-check` | Verify token is valid |
| `make kite-size CAPITAL=30000` | Calculate sizing |
| `make prelive-gate` | Pre-flight checks |
| `make kite-canary-launch` | Launch sequence (gate + watch) |
| `make kite-canary-status` | Check status anytime |
| `make kite-canary-stop` | Stop and flatten |
| `make watch-metrics` | Monitor heartbeats/leader |
| `make watch-all` | Monitor all metrics (unified) |
| `curl :8000/flatten -X POST` | Emergency flatten |
| `make burnin-report` | Generate daily report |

---

**TL;DR:** Token → Gate → Launch → Size → Enter 09:30-10:30 → Monitor → Flatten 15:25 → Report

**You're set for a safe, conservative LIVE canary tomorrow! 🚀**

---

## 📄 Ultra-Lean Reference

For a minimal, copy-paste ready checklist, see:
**`KITE_DAY1_TMINUS10.md`** — Keep this on a second screen tomorrow morning!

