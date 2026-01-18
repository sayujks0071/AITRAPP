# Deployment & Live Signals

## Philosophy
Strategy Foundry is a "Paper First" lab. It generates ideas and tracks them.
It does NOT connect to brokers.

## Live Signal JSON
Location: `packages/strategy_foundry/results/live_signal.json`

Schema:
```json
{
  "timestamp_ist": "2023-10-27T10:00:00+05:30",
  "champion_id": "a1b2c3d4",
  "instrument": "NIFTY",
  "signal": 1,
  "rule_summary": "Entry: supertrend | Filter: ADX>20",
  "risk": { "stop_loss_pct": 2.0, ... },
  "status": "OK"
}
```
`signal`: 1 (Long), -1 (Short), 0 (Flat).

## Gating
Signals are only published if:
1. Market is OPEN (IST).
2. A valid Champion exists.
3. Data is fresh.

## Consumption
To use these signals in `packages/core`:
1. Enable `ENABLE_LIVE=true` in env.
2. Create `approvals/ALLOW_LIVE.txt`.
3. Implement a bridge that reads `live_signal.json` and converts to `packages.core.models.Signal`.
(This bridge is currently NOT implemented).
