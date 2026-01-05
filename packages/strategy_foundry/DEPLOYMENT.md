# Deployment & Live Trading

## Philosophy
Strategy Foundry is **Paper-First**. It does NOT execute orders. It only publishes "intent" via JSON.

## Signal Artifact
`packages/strategy_foundry/results/live_signal.json`

Schema:
```json
{
  "timestamp_ist": "2023-10-27T10:00:00+05:30",
  "champion_id": "a1b2c3d4...",
  "instrument": "NIFTY",
  "signal": 1, // 1=LONG, 0=FLAT
  "rule_summary": "EMA Cross (10/20) + ATR Stop",
  "status": "OK"
}
```

## Consumption
To trade live:
1. Ensure `ENABLE_LIVE=true` in environment.
2. Ensure `approvals/ALLOW_LIVE.txt` exists.
3. Core system (external to this module) reads `live_signal.json`.
4. Core system validates market hours, risk limits, and executes via Broker API.

## Gating
- Signals are only published if the Champion meets strict robust criteria (Sharpe > 1.0, MaxDD < 25%).
- Signals are "SKIPPED" if market is closed or holiday.
