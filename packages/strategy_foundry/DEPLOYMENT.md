# Deployment & Live Signals

## Philosophy
**Paper First**. The Foundry generates signals but does NOT execute them.

## Signal Artifact
`packages/strategy_foundry/results/live_signal.json`

Schema:
```json
{
  "timestamp_ist": "2023-10-27T09:15:00+05:30",
  "champion_id": "ab123...",
  "signal": 1,
  "status": "OK"
}
```

## Live Execution Bridge (Gated)
To enable real execution (Optional):
1. Set `ENABLE_LIVE=true` in environment.
2. Create `approvals/ALLOW_LIVE.txt`.
3. Implement a core adapter to read the JSON and place orders.

**Default is OFF.**
