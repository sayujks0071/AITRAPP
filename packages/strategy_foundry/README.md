# Strategy Foundry
Self-generating strategy lab that evolves, ranks, and publishes trading signals.

## Architecture
- **Data**: Fetches daily data from Yahoo Finance via `requests`. Caches to CSV.
- **Factory**: Generates random strategy candidates from a "grammar" of Trend, Mean Reversion, and Risk blocks.
- **Backtest**: Vectorized engine with Walk-Forward Analysis (WFA) to test robustness.
- **Selection**: Ranks candidates by OOS Sharpe, Calmar, and Stability. Promotes "Champions".
- **Live**: Publishes JSON signals (`live_signal.json`) for the champion strategy. NO direct order execution.

## Running Locally
```bash
# Install dependencies
pip install -r requirements.txt
pip install requests

# Run once
export PYTHONPATH=.
python -m packages.strategy_foundry.run_hourly
```

## Environment Variables
- `FAST_MODE=1`: Runs a smaller batch (10 candidates, 2 folds) for quick testing/CI.

## Outputs
Artifacts are saved in `packages/strategy_foundry/results/`:
- `runs/<timestamp>/`: detailed metrics and candidates.
- `champions/`: versioned champion strategies.
- `leaderboard.md`: current top strategies.
- `live_signal.json`: current trading signal (if market open).
