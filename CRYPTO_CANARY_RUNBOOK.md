# Crypto Canary Runbook — Pre-Flight → Launch → Watch → Wrap

## Pre-Flight (90 seconds)

```bash
# 0) Infra + deps
docker compose up -d postgres redis
source venv/bin/activate && pip install -r requirements.txt

# 1) Automated GO/NO-GO
make crypto-gonogo

# Expect: ✅ PASS on ready, leader==1, all heartbeats<5s, orphans==0, flatten p95<2s
```

**If PASS → continue. If not, see "Quick Triage" below.**

---

## Launch (Canary LIVE: BTCUSDT Only)

```bash
# 2) Canary config
cp configs/crypto_canary_live.yaml configs/app.yaml

# 3) Env (use your IP-locked keys)
export APP_MODE=CRYPTO_LIVE APP_TIMEZONE=UTC PYTHONPATH=.
export KRAKEN_API_KEY="***" KRAKEN_API_SECRET="***"

# 4) Start API
make crypto-paper &

sleep 10 && curl -fsS http://localhost:8000/ready | jq  # expect 200
```

---

## First 10 Minutes — Watch Loop

```bash
make watch-crypto

# Healthy:
# trader_is_leader 1
# trader_.*heartbeat_seconds < 5
# trader_oco_orphans_total 0
# trader_crypto_ws_reconnects_total stays flat (≤1/10m)
# crypto_flatten_duration_seconds_count increments only when used; p95 < 2s
```

**Spread guard:** Entries should auto-skip when `(ask/bid - 1) > 0.005`. You'll see rejects logged; no action needed unless it's persistent.

---

## Tripwires & Rollback

```bash
# Panic flatten (should finish ≤2s)
curl -fsS -X POST http://localhost:8000/flatten | jq

# Quick metrics probe
curl -s http://localhost:8000/metrics | grep -E '^trader_(is_leader|.*heartbeat.*|oco_orphans_total|crypto_ws_reconnects_total)'

# Roll back to PAPER if needed
export APP_MODE=CRYPTO_PAPER
pkill -f 'uvicorn' || true
make crypto-paper &
```

---

## Post-Canary Wrap (at ~60–90 min)

```bash
make score-crypto-day1
make crypto-report

# Reports land in reports/burnin/ and reports/crypto/
```

---

## Quick Triage

### GO/NO-GO fails on heartbeats
- Restart API
- Confirm no duplicate instance
- Check local clock (`date`)
- Verify WS connected (reconnects shouldn't spike)

### Orphans > 0
- `curl -X POST http://localhost:8000/flatten`
- Watch `trader_oco_orphans_total` drop to 0
- Investigate logs for missed sibling cancel

### WS reconnects >3/10m
- Network jitter or exchange hiccups
- Wait for stability (backoff+jitter is enabled) or pause canary

### Spread guard rejects most entries
- Market illiquid/volatile
- This is expected protection—keep observing or loosen after soak

---

## Safety Checklist (Already Wired)

- ✅ Spot-only, no leverage
- ✅ minNotional/precision enforced
- ✅ 50 bps spread guard with orderbook cache
- ✅ OCO emulation + orphan detector
- ✅ Kill-switch `/flatten` with duration histogram & alerts
- ✅ Canary limits:
  - Per-trade: 0.15%
  - Heat: 0.5%
  - Daily stop: −0.75%
  - Max positions: 1
  - Symbols: BTCUSDT only

---

## Expected Metrics (Healthy State)

```bash
# Run this to see all critical metrics at once
curl -s http://localhost:8000/metrics | grep -E '^trader_(is_leader|.*heartbeat.*|oco_orphans_total|crypto_ws_reconnects_total|crypto_flatten_duration_seconds)' | sort
```

**Expected output:**
```
trader_is_leader{instance_id="..."} 1
trader_marketdata_heartbeat_seconds 0.5
trader_order_stream_heartbeat_seconds 1.2
trader_scan_heartbeat_seconds 2.1
trader_oco_orphans_total{venue="KRAKEN_SPOT"} 0
trader_crypto_ws_reconnects_total{venue="KRAKEN_SPOT"} 0
trader_crypto_flatten_duration_seconds_bucket{venue="KRAKEN_SPOT",le="0.1"} 0
trader_crypto_flatten_duration_seconds_bucket{venue="KRAKEN_SPOT",le="0.5"} 0
trader_crypto_flatten_duration_seconds_bucket{venue="KRAKEN_SPOT",le="1.0"} 0
trader_crypto_flatten_duration_seconds_bucket{venue="KRAKEN_SPOT",le="2.0"} 1
trader_crypto_flatten_duration_seconds_bucket{venue="KRAKEN_SPOT",le="5.0"} 1
trader_crypto_flatten_duration_seconds_bucket{venue="KRAKEN_SPOT",le="10.0"} 1
trader_crypto_flatten_duration_seconds_bucket{venue="KRAKEN_SPOT",le="+Inf"} 1
trader_crypto_flatten_duration_seconds_count{venue="KRAKEN_SPOT"} 1
trader_crypto_flatten_duration_seconds_sum{venue="KRAKEN_SPOT"} 0.85
```

---

## First Order Checklist (If Placing Test Order)

- [ ] Order size respects 0.15% per-trade limit
- [ ] OCO arms correctly (stop + TP)
- [ ] Spread guard allows entry (spread < 50 bps)
- [ ] Flatten completes ≤2s when invoked
- [ ] No orphans after OCO lifecycle

---

## Success Criteria (After 60-90 min)

- ✅ All heartbeats < 5s (stable)
- ✅ 0 orphans throughout
- ✅ WS reconnects ≤ 1/hr
- ✅ Spread guard working (rejects when spread > 50 bps)
- ✅ Flatten p95 < 2s
- ✅ Scorer JSON shows `"status":"PASS"`
- ✅ No precision/minNotional violations

---

## Next Steps (After Clean Canary)

1. **Extend to full day** if metrics stay green
2. **Add ETHUSDT** after 24-48h clean run with BTCUSDT
3. **Gradually increase limits** (per-trade → 0.20%, heat → 0.75%) after proven stability
4. **Full LIVE** only after 48-72h clean canary with expanded symbols

---

## Emergency Contacts

- **Kill switch**: `curl -X POST http://localhost:8000/flatten`
- **Rollback**: `export APP_MODE=CRYPTO_PAPER && pkill -f 'uvicorn' && make crypto-paper &`
- **Health check**: `make crypto-gonogo`
- **Metrics**: `make watch-crypto`


