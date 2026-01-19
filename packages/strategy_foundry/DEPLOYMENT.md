# Deployment & Live Signals

## Architecture
Strategy Foundry operates in isolation from the execution core. It produces a JSON artifact (`live_signal.json`) which acts as the interface.

## Live Signal JSON
Location: `packages/strategy_foundry/results/live_signal.json`

Schema:
```json
{
  "timestamp_ist": "2025-01-01T10:00:00+05:30",
  "champion_id": "...",
  "instrument": "NIFTY",
  "signal": 1,         // 1 (Long), -1 (Short), 0 (Flat)
  "rule_summary": "...",
  "status": "OK",      // or "SKIPPED"
  "reason": "..."
}
```

## Gating Logic
A signal is only published if:
1. **Market is Open**: 09:15 - 15:30 IST (Mon-Fri, non-holiday).
2. **Champion Exists**: A champion strategy has been selected.
3. **Champion is Eligible**:
   - OOS Sharpe >= 1.0
   - Max Drawdown <= 25%
   - Consistent profitability in OOS folds.

## Consumption (Bridge)
To enable live trading based on this signal:
1. An external orchestrator (in `packages.core`) must read `live_signal.json`.
2. `ENABLE_LIVE=true` must be set in environment.
3. `approvals/ALLOW_LIVE.txt` must exist.
4. Core risk checks must pass.

By default, Strategy Foundry **does not** connect to any broker.
