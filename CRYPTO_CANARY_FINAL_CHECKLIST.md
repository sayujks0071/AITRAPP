# Crypto Canary — Final Checklist (30-Second Pre-Launch)

## 30-Second Pre-Launch Smoke

```bash
# Keys & clock
echo "${KRAKEN_API_KEY:?}" >/dev/null && echo "${KRAKEN_API_SECRET:?}" >/dev/null

date -u && python - <<'PY'
import time
import datetime as dt
print("Drift(s)~", abs(time.time() - dt.datetime.utcnow().timestamp()))
PY

# Router & venue sanity
curl -fsS http://localhost:8000/health | jq '{mode,crypto_venue,allowed_symbols,precision:.crypto_precision,fees:.crypto_fees}'

make crypto-gonogo
```

**Green =** drift < ~2s, `mode` matches, venue shows BTC/USDT with sane precision/fees, `crypto-gonogo` PASS.

---

## Launch (One Command)

```bash
make crypto-canary-launch
```

---

## First 10 Minutes — "Good" Looks Like

- ✅ `trader_is_leader = 1`
- ✅ All three heartbeats `< 5s`
- ✅ `trader_oco_orphans_total = 0`
- ✅ `trader_crypto_ws_reconnects_total ≤ 1/10m`
- ✅ `crypto_flatten_duration_seconds` p95 `≤ 2s` (histogram present)
- ✅ Spread guard occasionally skips entries when spread > 50 bps (expected; not an error)

**Quick watch:**
```bash
make watch-crypto
```

---

## Tripwires → Immediate Action

### WS reconnect spike (>3 in 10m) OR any orphan > 0
- **Action**: `make crypto-canary-stop` (flattens + stops) → relaunch once
- **If repeats**: Pause canary, investigate

### Spread guard blocking continuously ≥5m
- **Action**: Stay up (that's protection), do not force fills
- **Why**: Market illiquid/volatile; protection is working

### Flatten p95 > 2s OR heartbeats ≥ 5s
- **Action**: Stop, investigate router/backoff/network
- **Check**: Router logs, network connectivity, exchange status

---

## Post-Canary Wrap (After 60–90 min)

```bash
make score-crypto-day1
make crypto-report
```

**Promote only if:**
- ✅ PASS
- ✅ orphans = 0
- ✅ reconnects low
- ✅ SLOs met

---

## Tiny Hardeners (Optional but Quick)

- ✅ Pin your canary symbol: keep **BTCUSDT only** today
- ✅ Export `TZ=UTC` in your shell profile for consistent timestamps
- ✅ Confirm Kraken API keys are **IP-locked** and **withdrawals disabled**

---

## Quick Smoke Test Script

```bash
#!/bin/bash
# 30-second pre-launch smoke test

set -euo pipefail

echo "🔍 30-Second Pre-Launch Smoke Test"
echo "=================================="
echo ""

# 1. Keys
echo "1️⃣  Checking API keys..."
echo "${KRAKEN_API_KEY:?}" >/dev/null && echo "${KRAKEN_API_SECRET:?}" >/dev/null
echo "   ✅ API keys set"
echo ""

# 2. Clock drift
echo "2️⃣  Checking clock drift..."
DRIFT=$(python3 - <<'PY'
import time
import datetime as dt
drift = abs(time.time() - dt.datetime.utcnow().timestamp())
print(f"{drift:.2f}")
PY
)

if (( $(echo "$DRIFT < 2.0" | bc -l) )); then
    echo "   ✅ Clock drift: ${DRIFT}s (< 2s)"
else
    echo "   ⚠️  Clock drift: ${DRIFT}s (>= 2s, check NTP)"
fi
echo ""

# 3. UTC time
echo "3️⃣  UTC time:"
date -u
echo ""

# 4. Health check (if API running)
echo "4️⃣  Router & venue sanity..."
if curl -fsS http://localhost:8000/health > /dev/null 2>&1; then
    curl -fsS http://localhost:8000/health | jq '{mode,crypto_venue,allowed_symbols,precision:.crypto_precision,fees:.crypto_fees}'
    echo "   ✅ Health check passed"
else
    echo "   ℹ️  API not running (will start during launch)"
fi
echo ""

# 5. GO/NO-GO
echo "5️⃣  Running GO/NO-GO check..."
if make crypto-gonogo; then
    echo ""
    echo "✅ All checks PASSED - Ready to launch!"
else
    echo ""
    echo "❌ GO/NO-GO check FAILED - Fix issues before launching"
    exit 1
fi
```

Save as `scripts/crypto_prelaunch_smoke.sh` and run:
```bash
chmod +x scripts/crypto_prelaunch_smoke.sh
./scripts/crypto_prelaunch_smoke.sh
```

---

## Launch Sequence

```bash
# 1. Pre-launch smoke (30 seconds)
./scripts/crypto_prelaunch_smoke.sh

# 2. Launch (one command)
make crypto-canary-launch

# 3. Watch (first 10 minutes)
make watch-crypto
```

---

## Rollback Triggers Summary

| Trigger | Action |
|---------|--------|
| WS reconnect spike (>3/10m) | `make crypto-canary-stop` → relaunch once |
| Any orphan > 0 | `make crypto-canary-stop` → relaunch once |
| Spread guard blocking ≥5m | Stay up (protection working) |
| Flatten p95 > 2s | Stop, investigate |
| Heartbeats ≥ 5s | Stop, investigate |

---

**You're clear to go. Run `make crypto-canary-launch`, keep the watch pane open for 10 minutes, and stick to the rollback triggers above.**


