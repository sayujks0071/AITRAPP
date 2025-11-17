# Binance Crypto Paper Trading - Quick Start

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
> * Create testnet keys, then also set:
>   `export BINANCE_TESTNET=1`
> * (Our adapter routes to testnet endpoints when this is set.)

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
* **Emergency stop:**

  ```bash
  make crypto-canary-stop   # safe flatten + shutdown
  ```

---

## Optional (CI Helpers)

* From a PR comment: `/crypto-health` runs the health+scorer and uploads artifacts.
* Scheduled health: `.github/workflows/crypto-health.yml` already in place.

---

## Quick Reference

### Check Status
```bash
make crypto-canary-status  # If available
curl -s http://localhost:8000/health | jq
curl -s http://localhost:8000/metrics | grep -E "trader_(is_leader|crypto_|binance_)" | head -20
```

### View Logs
```bash
# If running in background, check logs
tail -f logs/app.log  # or wherever logs are written
```

### Stop Safely
```bash
make crypto-canary-stop
# OR
pkill -f "uvicorn.*api.main"
```

---

You're set. Load keys, run **B → C → D**, and share any console snippets if something looks off.


