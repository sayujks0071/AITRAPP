# Deployment & Live Operation

## Philosophy
**"Paper First, Live Later"**
This module defaults to safe mode. It does NOT place orders.

## Signal Artifact
The output `live_signal.json` looks like:
```json
{
  "signal": 1,
  "instrument": "NIFTY",
  "status": "OK",
  ...
}
```
- `signal`: 1 (Long), -1 (Short), 0 (Neutral).
- `status`: OK or SKIPPED (Market closed, etc).

## Gating for Live Trading (Future)
To enable actual execution in `packages/core`:
1. `ENABLE_LIVE=true` environment variable must be set.
2. `approvals/ALLOW_LIVE.txt` file must exist.
3. Core bridge reads `live_signal.json` and places orders via `ExecutionEngine`.

## CI/CD
Runs hourly via GitHub Actions.
- **PRs**: Runs in `FAST_MODE` to verify code.
- **Schedule**: Runs full generation cycle hourly.
