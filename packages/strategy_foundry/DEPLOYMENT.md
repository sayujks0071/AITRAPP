# Deployment Guide

## Live Signals

The foundry publishes a signal artifact to `packages/strategy_foundry/results/live_signal.json`.
This file is generated ONLY during market hours and if a valid champion exists.

**Format:**
```json
{
  "timestamp_ist": "2023-10-27 10:15:00",
  "champion_id": "a1b2c3d4",
  "signal": 1,
  "status": "OK"
}
```

## Execution

Live execution is **OFF** by default.
To enable execution, an external system must read `live_signal.json` and verify:
1. `ENABLE_LIVE=true` environment variable.
2. `approvals/ALLOW_LIVE.txt` exists.

## Automation

The process is scheduled to run hourly via GitHub Actions.
