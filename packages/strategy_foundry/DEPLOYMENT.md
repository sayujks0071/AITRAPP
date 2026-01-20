# Deployment & Live Signals

## Architecture

The Foundry is a "Paper First" lab. It runs in isolation (GitHub Actions) and produces artifacts.

`run_hourly.py` -> Generates/Selects -> `live_signal.json`

## Signal JSON Schema

```json
{
  "timestamp_ist": "2023-10-27T10:00:00+05:30",
  "champion_id": "a1b2c3d4",
  "signal": 1,  // 1: Long, 0: Flat, -1: Short
  "status": "OK", // or SKIPPED
  "reason": ""
}
```

## Gating

Live signals are published ONLY if:
1. **Market Open**: 09:15 - 15:30 IST (Mon-Fri, non-holiday).
2. **Champion Eligible**:
   - OOS Sharpe >= 1.2
   - MaxDD <= 20%
   - Stable performance across folds.

## Safety

- **No Auto-Execution**: The foundry writes a file. It does not call broker APIs.
- **Environment Isolation**: Runs in a separate process/container.
- **Fail-Safe**: If data is stale or missing, signal is SKIPPED.
