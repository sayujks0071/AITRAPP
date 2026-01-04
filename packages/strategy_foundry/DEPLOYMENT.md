# Deployment

## Live Signal
The artifact `packages/strategy_foundry/results/live_signal.json` is the ONLY output for live trading.

## Consumption
To use this signal:
1. Ensure `ENABLE_LIVE=true` in environment.
2. Ensure `approvals/ALLOW_LIVE.txt` exists.
3. Write a bridge script that reads the JSON and calls Core execution logic.

## Safety
- Signals are "SKIPPED" if market is closed or data is unavailable.
- Strategy ID and Rule Summary are included for audit.
