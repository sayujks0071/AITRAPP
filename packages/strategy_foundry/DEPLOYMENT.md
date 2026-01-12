# Deployment & Live Trading

## Default State
**Live Trading is OFF by default.**
The system only publishes signals to `results/live_signal.json`.

## Enabling Live Execution (Bridge)
To enable the execution bridge (if implemented in Core), you must:
1. Set `ENABLE_LIVE=true` in environment variables.
2. Create `approvals/ALLOW_LIVE.txt` in the repository root.

## Signal Consumption
External systems or the Core execution engine should poll `results/live_signal.json`.

Schema:
```json
{
  "timestamp_ist": "2023-10-27T10:00:00+05:30",
  "champion_id": "md5_hash",
  "signal": 1, // 1: Long, 0: Flat, -1: Short
  "status": "OK"
}
```

## Safety
- Signals are only generated during market hours.
- Signals are skipped if no champion meets the strict promotion criteria.
- Hard close at 15:25 IST is enforced.
