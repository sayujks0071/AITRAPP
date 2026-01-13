# Deployment & Live Bridge

## Signal Artifact
The foundry publishes `packages/strategy_foundry/results/live_signal.json`.

Schema:
```json
{
  "timestamp_ist": "2023-10-27T10:15:00.123456",
  "champion_id": "a1b2c3d4",
  "signal": 1, // 1=Long, 0=Flat, -1=Short (if enabled)
  "status": "OK"
}
```

## Live Execution (Optional)
To enable live execution:
1. Ensure Core system is running.
2. Set `ENABLE_LIVE=true` in environment.
3. Create `approvals/ALLOW_LIVE.txt` file.
4. Implement a bridge script that reads `live_signal.json` and calls Core API.

**Note**: By default, this package is READ-ONLY and does not place orders.
