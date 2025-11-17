# Crypto Canary Quick Start

## 2-Minute Pre-Launch Sanity

```bash
# Keys + infra
echo "${KRAKEN_API_KEY:?"Set KRAKEN_API_KEY"}" >/dev/null
echo "${KRAKEN_API_SECRET:?"Set KRAKEN_API_SECRET"}" >/dev/null
docker compose up -d postgres redis

# GO/NO-GO
make crypto-gonogo

# Expect: all PASS (ready=200, leader==1, heartbeats<5s, orphans==0, flatten p95<2s)
```

## Launch (One Command)

```bash
make crypto-canary-launch
```

## What "Good" Looks Like (First 10 min)

```bash
# Gauges
curl -s http://localhost:8000/metrics | grep -E '^trader_(is_leader|.*heartbeat.*|oco_orphans_total|crypto_ws_reconnects_total)'

# Expect:
# trader_is_leader 1
# trader_marketdata_heartbeat_seconds <5
# trader_order_stream_heartbeat_seconds <5
# trader_scan_heartbeat_seconds <5
# trader_oco_orphans_total 0
# trader_crypto_ws_reconnects_total ~0 (≤1/10m)

# Spread guard (rejects when spread>50 bps—this is protection, not an error)
tail -n 100 logs/app.log | grep -i 'spread guard' || true
```

## Panic / Rollback (Keep Handy)

```bash
# Kill-switch → flat in ≤2s
curl -fsS -X POST http://localhost:8000/flatten | jq

# Or use convenience command
make crypto-canary-stop

# Restart back to PAPER if needed
export APP_MODE=CRYPTO_PAPER
make crypto-paper &
```

## Convenience Commands

```bash
# Check status
make crypto-canary-status

# Stop and flatten
make crypto-canary-stop

# Watch metrics
make watch-crypto
```

## Security Reminders (Last Mile)

- ✅ Use **IP-locked** API keys with **trading only**; **no withdrawals**
- ✅ Keep `APP_TIMEZONE=UTC` for crypto; clock drift <2s (NTP script covers this)
- ✅ Leave canary limits as-is: **0.15% / 0.5% / −0.75% / 1 position (BTCUSDT only)**

## Post-Canary Wrap (After 60-90 min)

```bash
make score-crypto-day1
make crypto-report
```

## Success Criteria

- ✅ All heartbeats < 5s (stable)
- ✅ 0 orphans throughout
- ✅ WS reconnects ≤ 1/hr
- ✅ Spread guard working (rejects when spread > 50 bps)
- ✅ Flatten p95 < 2s
- ✅ Scorer JSON shows `"status":"PASS"`
- ✅ No precision/minNotional violations


