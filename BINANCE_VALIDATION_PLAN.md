# Binance Validation Plan — End-to-End (5-7 min)

## Do This Now (5-7 min)

```bash
# 0) Keys + infra
export BINANCE_API_KEY="your_key"
export BINANCE_API_SECRET="your_secret"
docker compose up -d postgres redis
source venv/bin/activate && pip install -r requirements.txt

# 1) Paper config (Binance)
cp configs/crypto_paper.yaml configs/app.yaml   # already set to BINANCE_SPOT

# 2) Preflight + launch
make crypto-gonogo
make crypto-canary-launch                        # starts API, waits for /ready

# 3) Watch (separate terminal)
make watch-crypto

# 4) OCO drill (native OCO on Binance)
make crypto-oco-drill

# 5) Score + report
make score-crypto-day1
make crypto-report
```

**PASS =** leader 1, heartbeats < 5s, **OCO orphans = 0**, WS reconnects low, flatten p95 ≤ 2s, scorer JSON "PASS".

---

## Binance Must-Haves (Wired)

### ✅ Time Sync & recvWindow
- Server time sync via `/api/v3/time` on startup and every 5 minutes
- `recvWindow=5000` (5 second window) on all signed endpoints
- Auto-resync on `-1021` timestamp errors

### ✅ Rate-Limit Headers
- Reads `X-MBX-USED-WEIGHT-1m` and `X-MBX-ORDER-COUNT-1m`
- Exposes gauges: `trader_binance_used_weight_1m`, `trader_binance_order_count_1m`
- Visible in `make watch-crypto`

### ✅ Listen-Key Keepalive
- User data stream listenKey expires at 60 min
- Keepalive every 30 minutes (renewed at 25 min mark)
- Auto-reconnect on 400/`-1125` errors
- Counter: `trader_binance_listenkey_renew_total`

### ✅ Filters from `exchangeInfo`
- Enforces **PRICE_FILTER**, **LOT_SIZE**, **MIN_NOTIONAL**
- Rounds prices/qty to tick/step **before** sending orders
- Applied to OCO siblings as well

### ✅ Native OCO Quirks
- OCO requires `price` (TP), `stopPrice`, and `stopLimitPrice`
- All prices rounded to tick_size before sending
- Handles **FILLED/PARTIALLY_FILLED/CANCELED** states
- Partial fills tracked in paper book

---

## Monitoring (Already Added)

### Prometheus Metrics
- ✅ `trader_binance_used_weight_1m` (gauge, from header)
- ✅ `trader_binance_order_count_1m` (gauge, from header)
- ✅ `trader_binance_listenkey_renew_total` (counter)
- ✅ `trader_oco_orphans_total` (already present; should remain 0)

### Alerts (Already Configured)
- ✅ **Reconnect spike:** >3 in 10m (`CryptoWSReconnectSpike`)
- ✅ **Weight near cap:** used_weight_1m > 1000 (warn), >1100 (crit)
- ✅ **OCO orphan:** >0 (crit) (`CryptoOCOOrphans`)

---

## CI/Ops Updates (Already Done)

- ✅ Updated `crypto-health.yml` with `BINANCE_API_KEY` and `BINANCE_API_SECRET`
- ✅ Secrets should be set in GitHub (self-hosted runner only)
- ✅ IP-allowlist should be set in Binance API management (trading only, withdrawals off)

---

## Go/No-Go for Binance Canary

**GO if:**
- ✅ Day-1 scorer PASS (paper)
- ✅ Weight/order-count stable
- ✅ Reconnects low
- ✅ OCO clean (0 orphans)
- ✅ Flatten p95 ≤ 2s

**NO-GO if:**
- ❌ Any orphan
- ❌ Frequent `-1021` (time) errors
- ❌ Weight spikes (>1100/1200)
- ❌ Heartbeat ≥ 5s

---

## When Ready to Canary LIVE

```bash
cp configs/crypto_canary_live.yaml configs/app.yaml   # set BINANCE_SPOT, BTCUSDT only
export APP_MODE=CRYPTO_LIVE APP_TIMEZONE=UTC
make crypto-gonogo
make crypto-canary-launch
```

---

## What to Watch

```bash
make watch-crypto

# Expect:
# trader_is_leader 1
# trader_*heartbeat_seconds < 5
# trader_oco_orphans_total 0
# trader_crypto_ws_reconnects_total low
# trader_binance_used_weight_1m < 1000 (warn if >1000)
# trader_binance_order_count_1m < 10 (typical)
# trader_binance_listenkey_renew_total (increments every 30 min)
```

---

## Troubleshooting

### `-1021` Timestamp Errors
- **Cause**: Clock drift > 5s
- **Fix**: Time sync runs every 5 min; check NTP
- **Action**: Verify `_server_time_offset` in logs

### Listen Key Expired (`-1125`)
- **Cause**: Keepalive failed or >60 min expired
- **Fix**: Auto-renewal every 30 min; check keepalive task
- **Action**: Verify `binance_listenkey_renew_total` increments

### Rate Limit Hit
- **Cause**: Weight > 1200 or order count > limit
- **Fix**: Check `binance_used_weight_1m` and `binance_order_count_1m`
- **Action**: Reduce request frequency or increase limits

### OCO Orphans
- **Cause**: One OCO leg filled, sibling not cancelled
- **Fix**: Orphan detector should catch this
- **Action**: Check `check_oco_orphans()` is running

---

**All Binance-specific hardening is complete. Ready to validate!**


