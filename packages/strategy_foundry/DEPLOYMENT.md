# Deployment & Live Signals

## Safety First
Strategy Foundry **NEVER** places real orders directly. It only publishes a signal file.

## Signal Flow
1. **Generation:** `run_hourly.py` evaluates the Champion.
2. **Publishing:** If Market is Open AND Champion is Promoted, writes to `results/live_signal.json`.
3. **Consumption:** (Optional) Core system reads JSON and executes via `TradingOrchestrator` if enabled.

## Enablement Gates
Live trading requires:
1. `ENABLE_LIVE=true` environment variable.
2. `approvals/ALLOW_LIVE.txt` file presence.
3. Core system kill-switches must pass.

## Market Hours
- Signals are only published during NSE Market Hours (09:15 - 15:30 IST).
- Holidays are respected (fetched from NSE or fallback).

## Artifacts
- `results/live_signal.json`: The current authoritative signal.
- `results/leaderboard.csv`: Current top strategies.
- `results/champions/`: Historical champions.
