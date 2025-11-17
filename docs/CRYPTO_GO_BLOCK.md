# Crypto Go-Block: Day-1 Run Sequence

This document provides a copy-paste run sequence for crypto spot trading on AITRAPP.

## Prerequisites

1. **Infrastructure**
   ```bash
   docker compose up -d postgres redis
   ```

2. **Environment**
   ```bash
   source venv/bin/activate
   pip install -r requirements.txt
   cp configs/crypto_paper.yaml configs/app.yaml
   ```

3. **Secrets** (for PAPER, use testnet keys)
   ```bash
   export KRAKEN_API_KEY="your_testnet_key"
   export KRAKEN_API_SECRET="your_testnet_secret"
   ```

## Day-1 Sequence

### 1. Start Infrastructure
```bash
docker compose up -d postgres redis
```

### 2. Start Paper Mode
```bash
make start-paper
# Or: uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Quick Monitor
```bash
watch -n 5 'curl -s http://localhost:8000/metrics | grep -E "^trader_(is_leader|marketdata_heartbeat_seconds|order_stream_heartbeat_seconds|scan_heartbeat_seconds|crypto_ws_reconnects_total|oco_orphans_total)" | sort'
```

### 4. OCO Drill (BTCUSDT, Paper)
```bash
# Inject a synthetic signal (if you have a script for this)
python scripts/synthetic_plan_injector.py --symbol BTCUSDT --side LONG --qty 0.001 --strategy ORB

# Or manually trigger via API (if endpoint exists)
curl -X POST http://localhost:8000/flatten | jq
```

### 5. Run Scorer
```bash
scripts/score_crypto_day1.sh
```

## Expected Output

### Metrics to Watch
- `trader_is_leader` = 1
- `trader_marketdata_heartbeat_seconds` < 5
- `trader_order_stream_heartbeat_seconds` < 5
- `trader_scan_heartbeat_seconds` < 5
- `trader_crypto_ws_reconnects_total` ≤ 5 (warning if > 5)
- `trader_oco_orphans_total` = 0

### Scorer PASS Criteria
- `/ready` returns 200
- All heartbeats < 5s
- Leader lock = 1
- OCO orphans = 0
- Risk gates respected

## Troubleshooting

### WebSocket Reconnects High
- Check network connectivity
- Verify exchange API status
- Review logs: `tail -f logs/aitrapp_crypto.log`

### OCO Orphans
- Check OCO group tracking
- Verify order cancellation logic
- Review exchange adapter logs

### Heartbeats Stale
- Check orchestrator scan loop
- Verify market data stream connection
- Review Redis connectivity

## Next Steps

After Day-1 PASS:
1. Review `reports/burnin/crypto_day1_YYYY-MM-DD.json`
2. Monitor for 24 hours
3. Run Day-2 scorer (if available)
4. Proceed to LIVE only after manual gate approval

## Notes

- **No LIVE automation**: LIVE switch remains manual-gate only
- **Spot-only**: No leverage, no perps in v1
- **24/7**: Crypto markets run continuously
- **Conservative defaults**: 0.25% per-trade, 1.0% heat, -1.25% daily stop


