# Deployment & Live Trading

## Philosophy
Strategy Foundry follows a **Paper-First** philosophy.
- It **never** places orders directly.
- It only publishes a signal artifact (`live_signal.json`).
- Core system is responsible for execution.

## Signal Artifact
The artifact is located at `packages/strategy_foundry/results/live_signal.json`.

Schema:
```json
{
  "timestamp_ist": "2023-10-27 09:30:00+05:30",
  "champion_id": "a1b2c3d4...",
  "instrument": "NIFTY",
  "signal": 1,
  "rule_summary": "Trend Following...",
  "status": "OK"
}
```
Signal values:
- `1`: Long
- `0`: Flat
- `-1`: Short

## Gating
Live signals are only published if:
1. Market is OPEN (Mon-Fri 09:15-15:30 IST).
2. A Champion exists.
3. Champion meets eligibility criteria:
   - OOS Sharpe >= 1.0
   - MaxDD <= 25%
   - At least 3 positive OOS folds.

## Consumption (Core Bridge)
To consume this signal in `packages/core`:
1. Ensure `ENABLE_LIVE=true` in environment.
2. Ensure `approvals/ALLOW_LIVE.txt` file exists.
3. Implement a poller that reads `live_signal.json` and syncs position.
