# Crypto Canary Ops Card — Final Pre-Flight → Launch → Watch → Wrap

## Final Pre-Flight (90s)

```bash
# Keys & infra
echo "${KRAKEN_API_KEY:?"Set KRAKEN_API_KEY"}" >/dev/null
echo "${KRAKEN_API_SECRET:?"Set KRAKEN_API_SECRET"}" >/dev/null
docker compose up -d postgres redis

# Go/No-Go
make crypto-gonogo     # expect all PASS
```

### Last-Mile Venue Checks (One-Time)

- ✅ **IP-lock**: API keys locked to your static IP; **withdrawals disabled**
- ✅ **Symbol mapping**: BTCUSDT ↔ Kraken's **XBT/USDT** mapping is correct in the adapter
- ✅ **Precision / minNotional**: Confirm router shows correct `tickSize/stepSize` in `/health`
- ✅ **Spread guard**: Orderbook cache live; reject threshold = **50 bps**; staleness >5s → allow
- ✅ **Time sync**: NTP drift < **2s** (your drift script covers it)
- ✅ **Backoff**: WS reconnect exponential backoff ≤ 60s with jitter is enabled

---

## Launch (One Command)

```bash
make crypto-canary-launch
```

---

## First 10-Minute Watch (What "Good" Looks Like)

```bash
# Gauges (repeat every ~30s)
curl -s http://localhost:8000/metrics | grep -E '^trader_(is_leader|.*heartbeat.*|oco_orphans_total|crypto_ws_reconnects_total)'

# Expect:
# trader_is_leader 1
# trader_marketdata_heartbeat_seconds <5
# trader_order_stream_heartbeat_seconds <5
# trader_scan_heartbeat_seconds <5
# trader_oco_orphans_total 0
# trader_crypto_ws_reconnects_total ~0 (≤1/10m)

# Flatten SLO (histogram present, p95 <= 2s under light load)
curl -s http://localhost:8000/metrics | grep '^trader_crypto_flatten_duration_seconds'
```

**Or use convenience command:**
```bash
make watch-crypto
```

---

## Tripwires → Instant Actions

### Spread > 50 bps (alert fires)
- **Action**: Let it **skip entries**; do nothing unless persistent
- **Why**: This is protection, not an error

### WS reconnect spike (>3 in 10m)
- **Action**: `make crypto-canary-stop`, relaunch
- **If repeats**: Pause canary, investigate network/exchange

### OCO orphans > 0
- **Action**: `make crypto-canary-stop` (flattens) → relaunch
- **Investigate**: Orphan cleanup logic in logs

---

## Stop / Status / Rollback

```bash
# Check status
make crypto-canary-status   # ready + key gauges

# Stop and flatten
make crypto-canary-stop     # flatten + stop uvicorn (safe rollback)

# Optional quick revert to PAPER
export APP_MODE=CRYPTO_PAPER && make crypto-paper &
```

---

## Post-Canary Wrap (60–90 min after start)

```bash
make score-crypto-day1
make crypto-report
```

**PASS Criteria:**
- ✅ leader == 1
- ✅ heartbeats < 5s
- ✅ **orphans == 0**
- ✅ **WS reconnects low (≤1/hr)**
- ✅ flatten p95 ≤ 2s

---

## Safety Features (Already Wired)

- ✅ `set -Eeuo pipefail` + `trap ERR` → auto-flatten on failure
- ✅ Keys validated up front → fail-fast safety
- ✅ Spot-only, no leverage
- ✅ minNotional/precision enforced
- ✅ 50 bps spread guard with orderbook cache
- ✅ OCO emulation + orphan detector
- ✅ Kill-switch `/flatten` with duration histogram & alerts
- ✅ Canary limits: 0.15% / 0.5% / −0.75% / 1 position (BTCUSDT only)

---

## Quick Reference

| Command | Purpose |
|---------|---------|
| `make crypto-gonogo` | Pre-flight GO/NO-GO check |
| `make crypto-canary-launch` | Launch canary (one command) |
| `make crypto-canary-status` | Check status + metrics |
| `make crypto-canary-stop` | Stop and flatten |
| `make watch-crypto` | Watch metrics in real-time |
| `make score-crypto-day1` | Run Day-1 scorer |
| `make crypto-report` | Generate 24h report |

---

## Health Check Script

```bash
# Quick health snapshot
curl -s http://localhost:8000/metrics | grep -E '^trader_(is_leader|.*heartbeat.*|oco_orphans_total|crypto_ws_reconnects_total)' | sort
```

**Expected output (healthy):**
```
trader_is_leader{instance_id="..."} 1
trader_marketdata_heartbeat_seconds 0.5
trader_order_stream_heartbeat_seconds 1.2
trader_scan_heartbeat_seconds 2.1
trader_oco_orphans_total{venue="KRAKEN_SPOT"} 0
trader_crypto_ws_reconnects_total{venue="KRAKEN_SPOT"} 0
```

---

## Emergency Contacts

- **Kill switch**: `curl -X POST http://localhost:8000/flatten`
- **Stop command**: `make crypto-canary-stop`
- **Status check**: `make crypto-canary-status`
- **Rollback**: `export APP_MODE=CRYPTO_PAPER && make crypto-paper &`

---

## Success Indicators

After 60-90 minutes, you should see:

1. **Metrics**: All heartbeats < 5s, 0 orphans, low reconnects
2. **Scorer**: `reports/burnin/crypto_day1_*.json` shows `"status":"PASS"`
3. **Report**: `reports/crypto/crypto_report_*.md` shows healthy status
4. **No violations**: No precision/minNotional errors in logs
5. **Spread guard**: Working (rejects when spread > 50 bps)

---

**You're clear to fly. Launch with `make crypto-canary-launch`, keep the watch pane open for 10 minutes, and you're in a safe, conservative canary.**


