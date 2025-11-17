# T-5: GO/NO-GO (Crypto Canary — BTCUSDT)

## GO if all true

- ✅ `curl http://localhost:8000/ready` returns `200`
- ✅ Metrics: `trader_is_leader 1`, all `*heartbeat_seconds < 5`
- ✅ `trader_oco_orphans_total 0`
- ✅ `crypto_flatten_duration_seconds` p95 < 2s (from your last flatten)
- ✅ Exchange keys present + (optionally) IP-locked

## NO-GO if any

- ❌ WS reconnects spike (`crypto_ws_reconnects_total` jumps >3/10m)
- ❌ Spread guard trips continuously (ask/bid − 1 > 0.5% most of the time)
- ❌ Any non-zero OCO orphans

---

# Launch (Copy-Paste)

```bash
# 0) Infra + deps
docker compose up -d postgres redis
source venv/bin/activate && pip install -r requirements.txt

# 1) Config → canary live (BTCUSDT only)
cp configs/crypto_canary_live.yaml configs/app.yaml

# 2) Env
export APP_MODE=CRYPTO_LIVE APP_TIMEZONE=UTC PYTHONPATH=.
export KRAKEN_API_KEY="***" KRAKEN_API_SECRET="***"

# 3) Start & validate
make crypto-paper &
sleep 10 && curl -fsS http://localhost:8000/ready | jq
```

---

# First 10 Minutes — What to Watch

```bash
make watch-crypto

# Expect steady:
# trader_is_leader 1
# trader_*heartbeat_seconds < 5
# trader_oco_orphans_total 0
# trader_crypto_ws_reconnects_total low and flat
```

**Watch for:**
- If spread > 50 bps frequently → entries should auto-skip (confirm in logs)
- Place a **tiny** canary order only if your plan does so—OCO should arm and flatten should stay ≤2s when invoked

---

# Tripwires & Rollback

```bash
# Panic flatten
curl -fsS -X POST http://localhost:8000/flatten | jq

# Health snapshot
curl -fsS http://localhost:8000/metrics | grep -E '^trader_(is_leader|.*heartbeat.*|oco_orphans_total|crypto_ws_reconnects_total|prelive_day2_pass|prelive_day2_age_seconds)'

# Rollback to PAPER if needed
export APP_MODE=CRYPTO_PAPER
pkill -f 'uvicorn' || true
make crypto-paper &
```

---

# After the Canary (Wrap in ~60–90 min)

```bash
make score-crypto-day1
make crypto-report

# Attach the generated report in PR for audit.
```

---

# Nice-to-Have (Fast Wins)

- In your exchange console, **IP-lock** the API key to the runner's public IP (doc: `docs/CRYPTO_SECURITY.md`)
- Verify new alerts in Grafana/Prometheus:
  - `CryptoSpreadTooWide`
  - `CryptoWSReconnectSpike`
  - `CryptoOCOOrphans`
  - `CryptoFlattenDurationSLOBreach`

---

# Quick Health Check Script

```bash
#!/bin/bash
# Quick GO/NO-GO check before canary launch

API="${API:-http://localhost:8000}"

echo "🔍 GO/NO-GO Check"
echo "================="
echo ""

# 1. Ready endpoint
echo "1️⃣  Checking /ready..."
READY=$(curl -s -o /dev/null -w "%{http_code}" "$API/ready")
if [ "$READY" = "200" ]; then
    echo "   ✅ /ready returns 200"
else
    echo "   ❌ /ready returns $READY"
    exit 1
fi
echo ""

# 2. Leader lock
echo "2️⃣  Checking leader lock..."
LEADER=$(curl -s "$API/metrics" | grep '^trader_is_leader' | awk '{print $2}')
if [ "$LEADER" = "1" ]; then
    echo "   ✅ trader_is_leader = 1"
else
    echo "   ❌ trader_is_leader = $LEADER (expected 1)"
    exit 1
fi
echo ""

# 3. Heartbeats
echo "3️⃣  Checking heartbeats (< 5s)..."
BAD=0
curl -s "$API/metrics" | grep '^trader_.*heartbeat_seconds' | while read line; do
    METRIC=$(echo "$line" | awk '{print $1}')
    VALUE=$(echo "$line" | awk '{print $2}')
    if (( $(echo "$VALUE >= 5" | bc -l) )); then
        echo "   ❌ $METRIC = ${VALUE}s (>= 5s)"
        BAD=1
    else
        echo "   ✅ $METRIC = ${VALUE}s"
    fi
done
if [ $BAD -eq 1 ]; then
    exit 1
fi
echo ""

# 4. OCO orphans
echo "4️⃣  Checking OCO orphans..."
ORPHANS=$(curl -s "$API/metrics" | grep '^trader_oco_orphans_total' | awk '{print $2}')
if [ -z "$ORPHANS" ] || [ "$ORPHANS" = "0" ]; then
    echo "   ✅ trader_oco_orphans_total = ${ORPHANS:-0}"
else
    echo "   ❌ trader_oco_orphans_total = $ORPHANS (expected 0)"
    exit 1
fi
echo ""

# 5. WS reconnects (check rate)
echo "5️⃣  Checking WS reconnects..."
RECONNECTS=$(curl -s "$API/metrics" | grep '^trader_crypto_ws_reconnects_total' | awk '{print $2}')
if [ -z "$RECONNECTS" ]; then
    RECONNECTS=0
fi
echo "   ℹ️  trader_crypto_ws_reconnects_total = $RECONNECTS"
if [ "$RECONNECTS" -gt 3 ]; then
    echo "   ⚠️  High reconnect count (check if spike in last 10m)"
fi
echo ""

# 6. Flatten duration (if available)
echo "6️⃣  Checking flatten duration..."
FLATTEN_P95=$(curl -s "$API/metrics" | grep 'trader_crypto_flatten_duration_seconds_bucket' | head -1)
if [ -n "$FLATTEN_P95" ]; then
    echo "   ℹ️  Flatten duration buckets available (check p95 < 2s)"
else
    echo "   ℹ️  No flatten duration data yet (will be available after first flatten)"
fi
echo ""

echo "✅ GO/NO-GO Check Complete"
echo ""
echo "If all checks passed, you're clear to proceed with canary launch."
```

Save as `scripts/crypto_gonogo_check.sh` and run:
```bash
chmod +x scripts/crypto_gonogo_check.sh
./scripts/crypto_gonogo_check.sh
```


