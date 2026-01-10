# Deployment & Live Signals

## Signal Artifact
The system publishes `packages/strategy_foundry/results/live_signal.json` when:
1. Market is Open (09:15 - 15:30 IST)
2. A valid Champion exists (Passed strict gates)
3. Champion logic generates a signal

## Gating
Live execution is **OFF** by default.
To consume signals for execution:
1. Set `ENABLE_LIVE=true` in environment.
2. Create `approvals/ALLOW_LIVE.txt` file.
3. Ensure Core kill-switches are inactive.

## Process
1. GitHub Actions runs hourly.
2. If new data available, strategy re-evaluated.
3. If signal generated, JSON is updated.
4. Downstream execution system (if any) reads JSON and executes.
