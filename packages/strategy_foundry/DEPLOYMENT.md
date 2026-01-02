# Deployment & Live Signals

## Philosophy

StrategyFoundry is a **Paper-First** system. It assumes no real money execution until explicit manual intervention or a separate bridge is configured.

## Live Signal Artifact

The system produces `packages/strategy_foundry/results/live_signal.json` when:
1. The market is open (NSE Trading Hours).
2. A valid Champion exists and passes safety gates (MaxDD < 25%).

### JSON Schema

```json
{
  "timestamp_ist": "2023-10-27T10:00:00+05:30",
  "champion_id": "a1b2c3d4",
  "instrument": "NIFTY",
  "signal": 1,  // 1: Long, 0: Flat/Exit, -1: Short (not used yet)
  "risk": {
      "stop_loss_atr": 2.0
  },
  "status": "OK",
  "reason": ""
}
```

## Consumption

To trade this signal:
1. **Manual:** Read the JSON file or check the logs.
2. **Automated (Core Bridge):** A separate process in `packages/core` (not enabled by default) can watch this file.
   - It requires `ENABLE_LIVE=true` env var.
   - It requires `approvals/ALLOW_LIVE.txt` file to exist.

## Safety Gates

- No signal is published if market is closed.
- No signal is published if the Champion's recent OOS performance shows > 25% MaxDD.
