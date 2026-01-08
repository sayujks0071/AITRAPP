# Deployment & Live Trading

## Safety First
Strategy Foundry is designed to be **Read-Only** regarding the broker. It does not place orders.

## Signal Artifact
The output is `packages/strategy_foundry/results/live_signal.json`.
Schema:
```json
{
  "timestamp_ist": "2023-10-27T10:00:00+05:30",
  "champion_id": "ab12cd34",
  "instrument": "NIFTY",
  "signal": 1, // 1: Long, -1: Short, 0: Neutral
  "rule_summary": "EMA_CROSS(fast=9, slow=20) AND RSI_FILTER(min=40)",
  "risk": {"stop": "ATR", "params": {"period": 14, "multiplier": 2}},
  "status": "OK"
}
```

## Consumption (Optional Bridge)
To trade these signals:
1. Ensure `ENABLE_LIVE=true` in environment.
2. Create `approvals/ALLOW_LIVE.txt` on the execution server.
3. Implement a reader in `packages/core` that polls `live_signal.json`.
   - Verify timestamp is fresh (< 5 mins old).
   - Verify champion ID matches trusted list (optional).
   - Execute order compliant with `packages/core/risk.py`.

## Gating
- If market is closed, status is "SKIPPED".
- If no champion meets the rigorous criteria (Sharpe > 1, etc.), status is "SKIPPED".
