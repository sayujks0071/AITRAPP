# Deployment Guide

## Live Signal Consumption

The Foundry produces `packages/strategy_foundry/results/live_signal.json`.
This file is an artifact. It does NOT execute trades.

### Schema
```json
{
  "signal": 1, // 1 (Long), -1 (Short), 0 (Flat) - Entry Signal
  "status": "OK",
  "champion_id": "...",
  "risk": { "stop": "ATR_TRAIL", ... }
}
```

## Integration with Execution Bridge

To enable auto-trading:
1. Ensure `ENABLE_LIVE=true` in env.
2. Ensure `approvals/ALLOW_LIVE.txt` exists.
3. Write a bridge script that polls `live_signal.json` and calls Core API.

**Note**: The Foundry is currently "Signal Only".
