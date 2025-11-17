# Crypto Quick Start - CRYPTO_PAPER

## 10-Minute Smoke Test

```bash
# 0) Infra + deps
docker compose up -d postgres redis
source venv/bin/activate && pip install -r requirements.txt

# 1) Config → CRYPTO_PAPER
cp configs/crypto_paper.yaml configs/app.yaml
export APP_MODE=CRYPTO_PAPER APP_TIMEZONE=UTC PYTHONPATH=.
export KRAKEN_API_KEY="your_key" KRAKEN_API_SECRET="your_secret"

# 2) Start & readiness
make crypto-paper &
sleep 10 && curl -fsS http://localhost:8000/ready | jq

# 3) Watch gauges (in another terminal)
make watch-crypto

# 4) OCO drill
make crypto-oco-drill

# 5) Scorer
make score-crypto-day1
cat reports/burnin/crypto_day1_*.json | jq
```

## PASS Criteria

- `trader_is_leader == 1`
- All heartbeats `< 5s`
- `trader_oco_orphans_total == 0`
- `trader_crypto_ws_reconnects_total` stays low (0–1/hr ideal)
- `/flatten` ≤ 2s and positions = 0
- Scorer JSON → `"status":"PASS"`

## Makefile Commands

- `make crypto-paper` - Start API in CRYPTO_PAPER mode
- `make score-crypto-day1` - Run crypto Day-1 scorer
- `make watch-crypto` - Watch crypto metrics in real-time
- `make crypto-oco-drill` - Run full OCO drill (inject + flatten + verify)
- `make crypto-report` - Generate report from last 24h scorer JSONs

## Slash Commands (GitHub)

- `/crypto-health` - Run crypto health checks + scorer
- `/crypto-oco` - Run crypto OCO drill (paper)
- `/crypto-report` - Compile last 24h crypto report

## Guardrails

- **Spot-only**: No leverage/perps
- **minNotional/precision**: Enforced in router
- **Spread guard**: 50 bps max (uses orderbook data)
- **24/7 ops**: No market hours gate
- **Paper engine**: Short-circuits real orders, simulates fills
- **Conservative defaults**: 0.25% per-trade, 1.0% heat, -1.25% daily stop

## Burn-In Plan

1. **Run smoke test** (10 min) - verify all PASS criteria
2. **Monitor 24-48h** - keep `make watch-crypto` running
3. **Target metrics**:
   - 0 orphans
   - ≤1 WS reconnect/hr
   - Clean OCO lifecycle
4. **After clean run** - consider canary LIVE (manual gate only)

## Troubleshooting

- **Orphans > 0**: Check OCO group tracking, verify cancel path hits both siblings
- **WS reconnects spike**: Check exponential backoff (60s max), verify ping/pong
- **Precision/minNotional errors**: Verify symbol metadata cache loaded at boot
- **Spread guard fails**: Check orderbook subscription, verify bid/ask data fresh

## Files

- Config: `configs/crypto_paper.yaml`
- Scorer: `scripts/score_crypto_day1.sh`
- Report: `scripts/crypto_report.sh`
- Injector: `scripts/synthetic_crypto_plan.py`
- Docs: `docs/CRYPTO_GO_BLOCK.md`


