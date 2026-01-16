# Strategy Foundry
A self-generating strategy lab for NIFTY/SENSEX.

## Overview
This module runs hourly to:
1. Fetch latest daily OHLC data (cached).
2. Generate random trading strategies (Trend, Mean Reversion).
3. Backtest them on Daily timeframe.
4. Perform Walk-Forward Evaluation to prevent overfitting.
5. Select a "Champion" based on OOS metrics.
6. Publish a signal JSON if market is open.

## Usage
### Run Locally
```bash
# Fast mode (fewer candidates, faster run)
export FAST_MODE=1
python -m packages.strategy_foundry.run_hourly
```

### Output
Artifacts are stored in `results/`:
- `runs/<timestamp>/`: Leaderboard, metrics.
- `champions/`: JSON files of promoted strategies.
- `live_signal.json`: The latest signal from the current champion.

## Architecture
- **Hybrid**: Reuses `packages.core` indicators/hours but owns its research logic.
- **Safe**: No real order placement. Only outputs JSON.
- **Deterministic**: Seeded randomness (where applicable) and stable token IDs.
