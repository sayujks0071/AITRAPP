# Deployment & Live Signals

## Philosophy
Strategy Foundry is designed to be **safe by default**. It does not connect to brokers or place orders. It outputs a "Signal Artifact" which can be consumed by downstream systems or humans.

## Live Signal Artifact
The hourly runner generates `packages/strategy_foundry/results/live_signal_{INSTRUMENT}.json`.

### Schema
```json
{
  "timestamp_ist": "2023-10-27T10:00:00+05:30",
  "champion_id": "ab1234...",
  "instrument": "NIFTY",
  "signal": 1,  // 1: LONG, 0: FLAT/NEUTRAL, -1: EXIT/SHORT
  "rule_summary": "Entry: [EMA_Cross...] ...",
  "risk": {"sl_atr": 2.0, ...},
  "status": "OK" // or "SKIPPED"
}
```

## Consumption
To use this signal for trading:
1. Ensure `ENABLE_LIVE=true` in environment.
2. Ensure `approvals/ALLOW_LIVE.txt` exists.
3. Write a bridge script that reads the JSON, verifies the timestamp is fresh (< 60 mins), and places orders via `packages/core`.

## Gating
Signals are only generated if:
1. Market is Open.
2. A valid Champion exists.
3. The Champion meets strict OOS criteria (Sharpe > 1.0, MaxDD < 25%).
