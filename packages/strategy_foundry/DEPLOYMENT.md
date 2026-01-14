# Deployment & Live Signals

## Philosophy
**Paper First**. The Strategy Foundry does NOT place orders. It only emits a signal JSON.

## Signal Artifact
The live signal is published to `packages/strategy_foundry/results/live_signal.json`.

Schema:
```json
{
  "status": "OK|SKIPPED",
  "reason": "...",
  "timestamp_ist": "ISO8601",
  "champion_id": "...",
  "instrument": "NIFTY",
  "signal": 1, // 1=Long, 0=Flat
  "risk": {
    "stop_loss": "...",
    "take_profit": "..."
  }
}
```

## Consumption (Optional Bridge)
To enable live trading (Bridge), the following conditions must be met:
1. Environment variable `ENABLE_LIVE=true`.
2. File `approvals/ALLOW_LIVE.txt` exists.

A separate process (e.g. in `packages/core`) would:
1. Read `live_signal.json`.
2. Verify timestamp is fresh (< 15 mins).
3. Verify champion ID matches approved list (optional).
4. Place orders via Broker API.

**Note**: This module contains NO broker connection code.
