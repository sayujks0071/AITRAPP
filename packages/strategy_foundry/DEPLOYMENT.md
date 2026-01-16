# Deployment & Live Signals

## Philosophy
The Foundry is **Signal-Only** by default. It produces artifacts but does not execute trades.

## Signal Artifact
File: `packages/strategy_foundry/results/live_signal.json`

Schema:
```json
{
  "timestamp_ist": "2023-10-27T10:00:00+05:30",
  "champion_id": "ab12cd34",
  "instrument": "NIFTY",
  "signal": 1,
  "status": "OK",
  "reason": ""
}
```

## Consumption
To connect to execution:
1. Ensure `ENABLE_LIVE=true` in environment.
2. Ensure `approvals/ALLOW_LIVE.txt` exists.
3. Use a bridge script to read `live_signal.json` and map `1` -> Long, `0` -> Flat.

## Gating
Signals are **SKIPPED** if:
- Market is Closed.
- Champion failed Sanity Checks.
- Champion metrics < Thresholds (Sharpe 1.2, DD 20%).
- Data is stale.
