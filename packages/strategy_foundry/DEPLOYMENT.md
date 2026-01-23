# Deployment & Live Signals

## Live Signal
The module does **NOT** place orders directly.
It publishes `packages/strategy_foundry/results/live_signal.json`.

Schema:
```json
{
  "timestamp_ist": "2023-10-27T10:00:00+05:30",
  "champion_id": "ab12cd34",
  "signal": 1,
  "risk": {
      "stop": 19500.5,
      "tp": 19600.0,
      "flat_by": "15:25"
  },
  "status": "OK"
}
```

## Gating
Live signals are only generated if:
1. Market is Open.
2. A valid Champion exists.
3. Champion meets strict promotion criteria (Sharpe > 1.2, etc.).

## Execution Bridge
To trade these signals, an external system (or `packages/core/execution.py` extension) must:
1. Read `live_signal.json`.
2. Verify `ENABLE_LIVE=true` env var.
3. Verify `approvals/ALLOW_LIVE.txt` existence.
4. Execute via Broker API.
