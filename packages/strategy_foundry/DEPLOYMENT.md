# Deployment & Live Trading

## Philosophy

Strategy Foundry follows a **Signal-Only** architecture. It does *not* execute trades. It produces a `live_signal.json` artifact that a separate execution system can consume.

## Signal Artifact

Location: `packages/strategy_foundry/results/live_signal.json`

Schema:
```json
{
  "NIFTY": {
    "timestamp_ist": "2023-10-27T10:00:00+05:30",
    "champion_id": "a1b2c3d4",
    "signal": 1,  // 1: Long, 0: Neutral, -1: Short
    "status": "OK"
  }
}
```

## Consumption (Conceptual)

To trade these signals:
1.  Ensure `ENABLE_LIVE=true` in environment.
2.  Ensure `approvals/ALLOW_LIVE.txt` exists.
3.  Read the JSON file periodically.
4.  If `timestamp` is fresh (< 15 mins) and `signal` differs from current position, execute.

## Gating

Champions are only eligible for live signaling if:
- OOS Sharpe >= 1.0
- Max Drawdown <= 25%
- Positive result in >= 3 OOS folds.
