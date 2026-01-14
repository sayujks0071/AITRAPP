# Deployment & Live Signals

## Signal Publishing
- **Schedule**: Hourly via GitHub Actions (09:00 - 16:00 IST).
- **Artifact**: `packages/strategy_foundry/results/live_signal.json`
- **Logic**:
  - Checks if market is open.
  - Loads current "Champion" strategy.
  - Fetches recent data (cache + fresh).
  - Replays backtest to determine current state (Position 1 or 0).
  - Publishes signal.

## Safety
- **No Execution**: The Foundry module NEVER places orders. It only writes JSON.
- **Bridge**: A separate process (if enabled) would consume the JSON.
- **Gating**:
  - `ENABLE_LIVE=true` env var required for any bridge.
  - `approvals/ALLOW_LIVE.txt` file required.

## Consumption
External tools or Core can read `live_signal.json`:
```json
{
  "timestamp_ist": "2023-10-27T10:00:00+05:30",
  "signal": 1,
  "status": "OK",
  ...
}
```
If `status` is `SKIPPED`, do nothing.
