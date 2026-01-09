# Deployment Guide

## Architecture
The Strategy Foundry runs autonomously on a schedule (GitHub Actions). It interacts with the outside world only via **Data Ingestion** (Yahoo Finance) and **Artifact Publishing** (`live_signal.json`).

## Artifacts
The primary output is `packages/strategy_foundry/results/live_signal.json`.

Schema:
```json
{
  "timestamp_ist": "2023-10-27T10:00:00+05:30",
  "champion_id": "md5_hash",
  "timeframe": "5m",
  "instrument": "NIFTY",
  "signal": 1,
  "status": "OK"
}
```
*   `signal`: 1 (Long), 0 (Flat), -1 (Short).
*   `status`: "OK" or "SKIPPED".

## Gating for Live Execution
To connect this to a live broker:

1.  **Bridge**: A separate process must watch `live_signal.json`.
2.  **Approvals**:
    *   `ENABLE_LIVE=true` environment variable.
    *   `approvals/ALLOW_LIVE.txt` presence.
3.  **Kill Switch**: Core system must have kill switches enabled.

## Paper Trading
Recommended first step is to consume `live_signal.json` and place paper orders (virtual execution) to verify signal timing and drift against backtest logs.
