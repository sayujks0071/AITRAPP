# Binance Canary — GO/NO-GO Gates

## Pre-Canary Validation (7-minute flight)

```bash
# Run validation flight
make crypto-validation-flight
```

**PASS Criteria:**
- ✅ `trader_is_leader == 1`
- ✅ All heartbeats `< 5s`
- ✅ `trader_oco_orphans_total == 0`
- ✅ `trader_binance_listenkey_renew_total` increments (~1 per 25-30 min)
- ✅ `trader_binance_used_weight_1m < 900`
- ✅ `trader_binance_order_count_1m` under caps
- ✅ Flatten p95 `≤ 2s`
- ✅ Scorer: `reports/burnin/crypto_day1_*.json` → `"status":"PASS"`

---

## Tripwires (Instant Action)

### `-1021` Timestamp Errors
- **Symptom**: Repeating after periodic sync
- **Action**: 
  - Check `trader_binance_time_skew_ms` (should be < 1000ms)
  - Verify NTP sync
  - Restart adapter if persistent
- **Auto-recovery**: One auto-resync on first `-1021`

### Reconnect Spike (>3/10m)
- **Symptom**: `trader_crypto_ws_reconnects_total` spikes
- **Action**: 
  - Investigate network stability
  - Pause, relaunch
- **Check**: `trader_binance_listenkey_renew_total` should be stable

### OCO Orphan > 0
- **Symptom**: `trader_oco_orphans_total > 0`
- **Action**: 
  - `make crypto-canary-stop` (safe flatten)
  - Relaunch once
- **Prevention**: Native OCO should prevent this; investigate if occurs

### Weight Near Cap (>1100/1200)
- **Symptom**: `trader_binance_used_weight_1m > 1100`
- **Action**: 
  - Throttle fan-out/burst
  - Retry later
- **Warning**: Alert fires at >1000

---

## Canary LIVE Launch

### Pre-LIVE Checklist

- [ ] API keys: **IP-locked**, trading-only, withdrawals disabled
- [ ] Time sync OK: `trader_binance_time_skew_ms < 1000`
- [ ] `recvWindow=5000` active (check logs)
- [ ] Filters enforced: PRICE_FILTER, LOT_SIZE, MIN_NOTIONAL
- [ ] Listen-key keepalive confirmed: `trader_binance_listenkey_renew_total` increments
- [ ] CI crypto health job passes (secrets scoped to self-hosted runner)
- [ ] Validation flight PASS

### Launch Commands

```bash
# 1) Switch to canary config
cp configs/crypto_canary_live.yaml configs/app.yaml

# 2) Set environment
export APP_MODE=CRYPTO_LIVE APP_TIMEZONE=UTC
export BINANCE_API_KEY="your_key"
export BINANCE_API_SECRET="your_secret"

# 3) GO/NO-GO check
make crypto-gonogo

# 4) Launch
make crypto-canary-launch
```

### Canary Limits

- **Per-trade risk**: 0.15% (tighter than PAPER 0.25%)
- **Portfolio heat**: 0.5% (tighter than PAPER 1.0%)
- **Daily stop**: -0.75% (tighter than PAPER -1.25%)
- **Max positions**: 1 (BTCUSDT only)
- **Symbols**: BTCUSDT only

---

## First 10 Minutes — Watch

```bash
make watch-crypto
```

**Expected:**
- `trader_is_leader = 1`
- All heartbeats `< 5s`
- `trader_oco_orphans_total = 0`
- `trader_binance_used_weight_1m < 900`
- `trader_binance_time_skew_ms < 1000`
- `trader_binance_listenkey_renew_total` stable (increments every 30 min)

**Tripwires:**
- Any orphan → stop immediately
- Weight > 1100 → throttle
- Time skew > 5000ms → check NTP
- Reconnects > 3/10m → investigate network

---

## Post-Canary Wrap (60-90 min)

```bash
make score-crypto-day1
make crypto-report
```

**Promote if:**
- ✅ Scorer PASS
- ✅ Orphans = 0
- ✅ Reconnects low
- ✅ SLOs met (flatten p95 ≤ 2s)
- ✅ No timestamp errors
- ✅ Weight stable

**Extend canary if:**
- ⚠️  Any warnings but no critical issues
- ⚠️  Need more data for confidence

**Rollback if:**
- ❌ Any orphan
- ❌ Frequent timestamp errors
- ❌ Weight spikes
- ❌ Heartbeat ≥ 5s

---

## Nice-to-Have Hardeners (Implemented)

- ✅ **ExchangeInfo cache**: TTL 5 min, auto-refresh on `-2010/-1111` errors
- ✅ **Idempotency keys**: SHA256 hash of clientOrderId for de-dupe
- ✅ **Time skew gauge**: `trader_binance_time_skew_ms` for visibility
- ✅ **Unit tests**: Rounding, minNotional, OCO lifecycle (see `tests/test_binance_spot.py`)

---

## Quick Reference

| Metric | Good | Warning | Critical |
|--------|------|---------|----------|
| `trader_is_leader` | 1 | 0 | - |
| Heartbeats | < 5s | 5-10s | > 10s |
| OCO orphans | 0 | - | > 0 |
| Time skew | < 1000ms | 1000-5000ms | > 5000ms |
| Used weight | < 900 | 900-1100 | > 1100 |
| WS reconnects | ≤ 1/hr | 2-3/hr | > 3/10m |
| Flatten p95 | ≤ 2s | 2-5s | > 5s |

---

**Ready to validate! Run `make crypto-validation-flight` to start.**


