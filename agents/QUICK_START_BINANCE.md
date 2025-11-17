# Binance Crypto Paper Trading - Quick Start Guide

## ✅ All Systems Ready

The Binance integration is fully wired and ready to run. Here's your copy-paste path:

---

## A) One-Time Prep (60-90s)

```bash
# 0) Infra + venv
docker compose up -d postgres redis
python3 -m venv .venv
source .venv/bin/activate
pip -q install -U pip && pip -q install -r requirements.txt
```

**Add your Binance keys (trading-only, IP-locked):**

```bash
export BINANCE_API_KEY="YOUR_BINANCE_KEY"
export BINANCE_API_SECRET="YOUR_BINANCE_SECRET"
```

> **Using Binance Spot Testnet instead?**
> 
> * Create testnet keys at https://testnet.binance.vision/
> * Then also set:
>   `export BINANCE_TESTNET=1`
> * (The adapter automatically routes to testnet endpoints when this is set.)

---

## B) Start Paper Trading (CRYPTO_PAPER)

```bash
# 1) Use Binance paper config
cp configs/crypto_paper.yaml configs/app.yaml

# 2) Mode + timezone
export APP_MODE=CRYPTO_PAPER APP_TIMEZONE=UTC PYTHONPATH=.

# 3) Pre-launch smoke (clock drift, readiness, GO/NO-GO)
make crypto-prelaunch-smoke

# 4) Launch API (paper mode)
make crypto-paper &

# 5) Readiness check
sleep 10 && curl -fsS http://localhost:8000/ready | jq
```

---

## C) Watch the Gauges (keep this running)

```bash
# Prometheus-style quick watch (heartbeats, reconnects, orphans, time skew, etc.)
make watch-crypto
```

**Targets for green state:**

* `trader_is_leader == 1`
* Heartbeats `< 5s`
* `trader_crypto_ws_reconnects_total` stays low (≤ 1/hr)
* `trader_oco_orphans_total == 0`
* `trader_binance_time_skew_ms < 1000`
* `trader_binance_used_weight_1m < 900` (rate limit headroom)

---

## D) OCO Drill (prove exits + flatten)

```bash
# Inject a tiny synthetic plan and verify OCO lifecycle + flatten ≤ 2s
make crypto-oco-drill
```

**Expected:**

* Positions return to **0**
* `crypto_flatten_duration_seconds` p95 ≤ **2s**
* No OCO orphans
* Native OCO on Binance (no client-side emulation needed)

---

## E) End-of-Session Wrap (reporting)

```bash
# Score Day-1 and compile report
make score-crypto-day1
make crypto-report

# Quick look
ls -1 reports/burnin/crypto_day1_*.json
ls -1 reports/crypto/*.md
```

---

## If Anything Trips

* **Missing keys / auth** → re-export `BINANCE_API_KEY/SECRET`
* **Clock drift** > 1s → ensure system time sync (NTP) and re-run smoke
* **Rate-limit warns** → the adapter backs off; it'll settle automatically
* **Spread guard blocks** → normal in illiquid moments; the order is skipped safely
* **Timestamp errors (-1021)** → adapter auto-resyncs; if persistent, check NTP
* **Listen key expiry (-1125)** → adapter auto-renews every 30min
* **Emergency stop:**

  ```bash
  make crypto-canary-stop   # safe flatten + shutdown
  ```

---

## Quick Status Check

```bash
# Check canary status
make crypto-canary-status

# Or manual check
curl -s http://localhost:8000/health | jq '.crypto_venue, .crypto_allowed_symbols'
curl -s http://localhost:8000/metrics | grep -E "trader_(is_leader|binance_time_skew_ms|binance_used_weight_1m)" | head -5
```

---

## What's Different with Binance

### Advantages
- ✅ **Native OCO** - No client-side emulation needed
- ✅ **Better rate limits** - 1200 weight/min, 10 orders/sec
- ✅ **Time sync** - Auto-syncs server time to prevent timestamp errors
- ✅ **Listen key keepalive** - Auto-renews every 30min
- ✅ **ExchangeInfo caching** - Reduces API calls, auto-refreshes on errors

### Monitoring
- Watch `binance_time_skew_ms` (should be < 1000ms)
- Watch `binance_used_weight_1m` (warn if > 900)
- Watch `binance_listenkey_renew_total` (should increment ~every 30min)

---

## Optional (CI Helpers)

* From a PR comment: `/crypto-health` runs the health+scorer and uploads artifacts.
* Scheduled health: `.github/workflows/crypto-health.yml` already in place.

---

## Next Steps After Paper Session

1. ✅ Review Day-1 scorer results
2. ✅ Check for any OCO orphans or WS reconnect spikes
3. ✅ Verify flatten duration < 2s
4. ⏭️ If all green, proceed to canary LIVE (with tight limits)

---

You're set. Load keys, run **B → C → D**, and share any console snippets if something looks off.


