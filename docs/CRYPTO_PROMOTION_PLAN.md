# Crypto Promotion Plan: PAPER → Canary LIVE

## Prerequisites (Must PASS)

After **24-48h clean PAPER burn-in**, verify:

- ✅ `trader_is_leader == 1` (consistent)
- ✅ All heartbeats `< 5s` (stable)
- ✅ `trader_oco_orphans_total == 0` (no orphans)
- ✅ `trader_crypto_ws_reconnects_total` ≤ 1/hr (stable connection)
- ✅ Spread guard working (entries skip when spread > 50 bps)
- ✅ `/flatten` completes ≤ 2s, positions = 0
- ✅ All `crypto_day1_*.json` reports show `"status":"PASS"`

## Canary LIVE Configuration

**File:** `configs/crypto_canary_live.yaml`

**Conservative Settings:**
- Per-trade risk: **0.15%** (tighter than PAPER's 0.25%)
- Portfolio heat: **0.5%** (tighter than PAPER's 1.0%)
- Daily stop: **-0.75%** (tighter than PAPER's -1.25%)
- Max positions: **1** (single position only)
- Symbols: **BTCUSDT only** (single symbol)
- Burst: **2 orders** (was 4 in PAPER)
- Fan-out: **4/s** (was 6/s in PAPER)

## Promotion Steps

### 1. Pre-Live Gate

```bash
# Verify PAPER burn-in is clean
make crypto-report
cat reports/crypto/crypto_report_*.md

# Check last 24h scorer JSONs
ls -lt reports/burnin/crypto_day1_*.json | head -5
for f in reports/burnin/crypto_day1_*.json; do
  echo "$f: $(jq -r '.status' "$f")"
done
```

**Gate Criteria:**
- Last 5 scorer JSONs all `"status":"PASS"`
- 0 orphans in last 24h
- WS reconnects ≤ 1/hr average
- No precision/minNotional violations

### 2. Switch to Canary LIVE

```bash
# Backup current config
cp configs/app.yaml configs/app.yaml.backup

# Switch to canary LIVE
cp configs/crypto_canary_live.yaml configs/app.yaml
export APP_MODE=CRYPTO_LIVE APP_TIMEZONE=UTC PYTHONPATH=.

# Verify config
cat configs/app.yaml | grep -A 5 "risk:"

# Start (manual operator action required)
make crypto-paper  # Note: command name is crypto-paper but mode is CRYPTO_LIVE
```

### 3. Monitor First Hour

```bash
# Watch metrics closely
make watch-crypto

# Check health every 5 minutes
watch -n 300 'curl -s http://localhost:8000/health | jq'

# Run scorer every 30 minutes
watch -n 1800 'make score-crypto-day1'
```

**First Hour Checklist:**
- [ ] Leader lock acquired
- [ ] All heartbeats < 5s
- [ ] WebSocket connected
- [ ] No order rejections
- [ ] Spread guard working
- [ ] OCO emulation working
- [ ] No orphans

### 4. First 24h Monitoring

- Monitor `make watch-crypto` continuously
- Run `make score-crypto-day1` every 30 minutes
- Generate `make crypto-report` at end of 24h
- Verify all metrics within acceptable ranges

## Rollback Plan

If issues detected:

```bash
# Immediate flatten
curl -X POST http://localhost:8000/flatten

# Switch back to PAPER
cp configs/crypto_paper.yaml configs/app.yaml
export APP_MODE=CRYPTO_PAPER

# Restart
# (restart API)
```

## Success Criteria (After 24h Canary)

- ✅ 0 orphans
- ✅ 0 order rejections (precision/minNotional)
- ✅ WS reconnects ≤ 1/hr
- ✅ All scorer JSONs PASS
- ✅ No spread guard violations
- ✅ Clean OCO lifecycle

## Next Steps (After Clean Canary)

1. **Expand symbols**: Add ETHUSDT (if BTCUSDT stable)
2. **Increase limits**: Gradually increase per-trade risk to 0.20%, heat to 0.75%
3. **Add strategies**: Enable additional strategies one at a time
4. **Full LIVE**: Only after 48-72h clean canary with expanded symbols

## Notes

- **Manual gate only**: No automation for LIVE switch (SEBI-style guardrails)
- **Conservative by design**: Canary settings are intentionally tight
- **Gradual expansion**: Increase limits only after proven stability
- **24/7 monitoring**: Crypto runs continuously, monitor accordingly


