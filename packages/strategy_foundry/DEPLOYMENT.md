# Deployment & Live Trading

## Philosophy
**Paper First**. The Strategy Foundry is designed to run autonomously and generate signals without executing them. Execution is handled by a separate core system or human intervention.

## Signal Artifact
The `live_signal.json` is the interface between the Foundry and the Execution Engine.

```json
{
  "timestamp_ist": "2023-10-27T10:00:00+05:30",
  "champion_id": "a1b2...",
  "instrument": "NIFTY",
  "signal": 1,
  "rule_summary": "...",
  "risk": {"stop_atr_mult": 3.0, ...},
  "status": "OK"
}
```

## Gating
Live execution (if implemented in core) must be gated by:
1. `ENABLE_LIVE=true` environment variable.
2. `approvals/ALLOW_LIVE.txt` file presence.
3. `live_signal.json` status being "OK".

## CI/CD
The `strategy_foundry_hourly.yml` workflow runs every hour:
1. Updates data.
2. Re-evaluates strategies.
3. Promotes new champion if significantly better.
4. Generates signal artifact.
