# Kite LIVE Canary - Day-1 Quick Reference

**Capital:** ₹20-50k | **Risk:** 0.30% per trade | **Daily Cap:** -1.50%

---

## 0) Tonight (2-min sanity check)

```bash
# Ensure venv + deps
source .venv/bin/activate 2>/dev/null || python3 -m venv .venv && source .venv/bin/activate
pip install -q -r requirements.txt

# Verify infrastructure (orchestrator, metrics, docker)
make verify-infra

# Smoke test token refresh script (no secrets, dry run)
make kite-token-smoke

# Dry-run the sizing calculator
make kite-size CAPITAL=30000 RISK_PCT=0.30
make kite-size CAPITAL=50000 RISK_PCT=0.30
```

**Expected outputs:**
- ₹30k → ~₹90 risk → net debit ≈ **₹3.60** per lot (cost ≈ ₹180 @ lot=50, 50% stop ≈ ₹90)
- ₹50k → ~₹150 risk → net debit ≈ **₹6.00** per lot (cost ≈ ₹300 @ lot=50, 50% stop ≈ ₹150)

---

## 1) Pre-Open (08:55-09:10 IST)

### Step 1: Login & Token (08:55 IST)
```bash
# 1) Refresh token (interactive - opens browser)
export KITE_API_KEY="***"
export KITE_API_SECRET="***"
make kite-token-refresh

# 2) Copy the printed export commands and paste:
export KITE_ACCESS_TOKEN="***"        # fresh token from today
export KITE_USER_ID="***"             # if provided

# 3) Quick self-check (verify token works)
make kite-token-check

# 4) Set remaining env vars
export APP_MODE=LIVE
export APP_TIMEZONE=Asia/Kolkata
export EXPECTED_EGRESS_IP="x.x.x.x"   # your allow-listed IP
```

**Morning Playbook (copy/paste):**
```bash
# 08:55 – refresh token
export KITE_API_KEY="***"
export KITE_API_SECRET="***"
make kite-token-refresh
# (copy the printed `export KITE_ACCESS_TOKEN="..."` + `export KITE_USER_ID="..."` and paste)

# Guardrails
export APP_MODE=LIVE
export APP_TIMEZONE=Asia/Kolkata
export EXPECTED_EGRESS_IP="x.x.x.x"

# Pre-open GO checks → ready → watch
make kite-canary-launch

# Status any time in another tab
make kite-canary-status
```

### Step 2: Health Gates
```bash
make prelive-gate                      # must PASS (egress, Day-2 PASS, heartbeats)
curl -fsS :8000/ready | jq            # ready: 200
make watch-metrics                    # leader==1, heartbeats <5s
```

**Or use the launch wrapper:**
```bash
make kite-canary-launch                # Does all checks + starts monitoring
```

---

## 2) Canary Window (09:30-10:30 IST)

**Strategy:** **NIFTY weekly debit spread** only (defined risk). One attempt, no re-entries.

### Sizing (use calculator output)

```bash
# Quick sizing check
make kite-size CAPITAL=30000 RISK_PCT=0.30
make kite-size CAPITAL=50000 RISK_PCT=0.30
```

**Target sizing:**
- **₹20–30k**: target risk **₹60–₹90** → net debit ≈ **₹1.2–₹1.8** per lot (stop 50%)
- **₹50k**: target risk **₹150** → net debit ≈ **₹6.0** per lot (stop 50%)

### Entry Guards

- **ORB(15) bias** + trend (e.g., EMA34>EMA89 for calls)
- **Spread ≤ 0.5%**, healthy volume/OI, **not in F&O ban**
- Engine gap ≥ **300 ms**, burst=2, ≤4 orders/sec (as per config)

### Exits

- **Stop:** −50% of net debit
- **TP:** +60–80% of net debit (use +70% for Day-1)
- **Timeout:** exit by **15:10–15:20** if still open
- **Hard flat:** **15:25** (system enforced)

### Tripwires → Instant Flatten

- Daily P&L ≤ −1.50%
- Any heartbeat ≥ 5s / stream stalls / duplicate orders
- OCO inconsistencies
- Leader changes (should be 0)

---

## 3) Post-Close (15:25+ IST)

```bash
make burnin-report && make reconcile-db && make post-close
make score-day2
```

**Capture:**
- Screenshots (fills, P&L, latency)
- Export logs/artifacts
- Note slippage vs quoted mid
- Note spread behavior at entry/exit

**Or use the stop wrapper:**
```bash
make kite-canary-stop                  # Flattens positions + stops API
```

---

## Config File

Use `configs/kite_canary_live.yaml` - it's pre-configured with all Day-1 parameters.

To load it, ensure your app reads configs from the `configs/` directory and this file is selected when `APP_MODE=LIVE`.

---

## Example Sizing (₹30k capital)

```
Risk per trade: ₹90 (0.30% of ₹30k)
Net debit/lot:  ₹3.60
Stop loss:      ₹1.80 (-50%)
Take profit:    ₹6.12 (+70%)
Total cost:     ₹180 for 1 lot (50 lots × ₹3.60)
```

**Look for spreads with:**
- Net debit ≈ ₹3.60 per lot
- Tight bid-ask (≤ 0.5%)
- Good liquidity (OI ≥ 50k, volume ≥ 100)

---

## Quick Commands

| Command | Purpose |
|---------|---------|
| `make verify-infra` | Verify infrastructure (orchestrator, metrics, docker) |
| `make kite-token-smoke` | Smoke test token script (dry run, no secrets) |
| `make kite-token-refresh` | Get fresh access token (daily) |
| `make kite-token-check` | Verify token is valid (quick self-check) |
| `make kite-size CAPITAL=30000` | Calculate sizing (quick) |
| `make prelive-gate` | Pre-flight checks |
| `make kite-canary-launch` | Launch sequence (gate + watch) |
| `make kite-canary-status` | Check status anytime |
| `make kite-canary-stop` | Stop and flatten |
| `make watch-metrics` | Monitor heartbeats/leader (equity) |
| `make watch-crypto` | Monitor crypto metrics (Binance) |
| `make watch-all` | Monitor all metrics (unified) |
| `curl :8000/ready` | Check API readiness |
| `curl :8000/flatten -X POST` | Emergency flatten |
| `make burnin-report` | Generate daily report |

---

## Tuning After Day-1

1. **Position sizing:** Adjust net debit to match target ₹ risk precisely
2. **Entry timing:** If ORB noisy, push to 9:35-9:45 or add vol-z/ATR buffer
3. **Targets:** Tighten TP to +50-60% if hard to fill; widen to +80-100% if moves outrun exits
4. **Liquidity guard:** Raise min volume/OI thresholds; discard wide-spread strikes
5. **Execution throttles:** Keep engine gap ≥250-350ms; small burst/fan-out

---

## What to Expect in Metrics

**Good signs:**
- `trader_is_leader` → **1**
- `*_heartbeat_seconds` all **< 5s**
- `trader_scan_ticks_total` → steadily rising
- `trader_leader_changes_total` → **0** (or stays flat after startup)
- `trader_oco_orphans_total` → **0**
- `crypto_flatten_duration_seconds` ≤ **2s** when tested
- Clean order lifecycle (enqueue→ACK→fill latencies logged)

**Watch commands:**
```bash
make watch-metrics    # Equity (Kite) metrics
make watch-crypto     # Crypto (Binance) metrics  
make watch-all        # Unified (all metrics)
```

**Check status anytime:**
```bash
make kite-canary-status                 # Shows ready endpoint + key metrics
```

## What Gets Captured

- **Per-order:** enqueue→ACK, ACK→fill latency; slippage vs mid; rejects/cancels
- **Per-trade:** MAE/MFE, time-in-trade, exit reason (stop/tp/timeout/manual)
- **Strategy:** ORB range stats, ATR/vol-z values, filter rejections
- **Ops:** reconnects, heartbeat p95, flatten duration histogram

---

## Fast Tweaks After Day-1

- **If fills were sticky** → start with slightly **tighter TP** (+50–60%) next day
- **If ORB noisy** → delay entries to **9:35–9:45** or raise **vol-z / ATR** buffer
- **If spreads wide** → increase min-liquidity filters or skip those strikes

---

## Troubleshooting Token Issues

**Common errors:**
- **"Request token expired"** → Use token within a few minutes of login
- **"Invalid token"** → Token expires daily at midnight IST - refresh each morning
- **"Redirect URI mismatch"** → Check Kite Connect app settings

**Quick fixes:**
- Restart the OAuth flow: `make kite-token-refresh`
- Verify token: `make kite-token-check`
- Check clock drift: `date` (should be within 2s of IST)

## Security Notes

- ✅ `.env` is in `.gitignore` (secrets safe)
- 💡 Consider `trap 'unset KITE_ACCESS_TOKEN' EXIT` for auto-cleanup
- 💡 Keep NTP synced (clock drift can cause token failures)
- 💡 Optional: Use macOS Keychain for token storage (future enhancement)

---

**TL;DR:** Tonight sanity → Login → Gate → Watch → One debit spread 09:30-10:30 → Monitor → Flatten 15:25 → Report

---

## 📋 Full Launch Checklist

For a complete, step-by-step launch checklist with timestamps, see:
**`KITE_DAY1_LAUNCH_CHECKLIST.md`** — Print this and keep it open tomorrow morning!

