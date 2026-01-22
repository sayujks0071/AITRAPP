# Deployment & Live Signals

## Philosophy
This system is designed to be **Signal First, Execution Second**.
It produces a JSON artifact (`live_signal.json`) representing the opinion of the current Champion strategy.

## Signal Publishing
- Runs hourly (or faster if scheduled).
- Checks if Market is Open (Asia/Kolkata).
- Checks if Champion is "Live Eligible" (Strict criteria: Sharpe > 1.2, Low DD, Stable).
- Writes `live_signal.json`.

## Consumption
- Core system (or external executor) can poll `live_signal.json`.
- **Safety**:
  - Do NOT execute blindly.
  - Verify `timestamp_ist` is fresh (< 5 mins old).
  - Verify `status` is "OK".
  - Verify `champion_id` matches expected.

## Live Execution Gating
To enable actual order placement (if implemented):
1. Environment variable `ENABLE_LIVE=true`.
2. File existence `approvals/ALLOW_LIVE.txt`.
3. Core safety checks passed.
