# Strategy Foundry

An autonomous "self-generating strategy lab" that runs hourly to discover, backtest, and promote trading strategies for NIFTY/SENSEX.

## Architecture

- **Factory**: Generates random strategies using a grammar of indicators (Trend, Mean Reversion, Risk).
- **Backtest**: Vectorized engine with Walk-Forward Evaluation (3-4 folds).
- **Selection**: Ranks strategies by Sharpe, Calmar, and Stability. Promotes "Champions".
- **Live**: Publishes `live_signal.json` artifacts. NO direct execution.

## Usage

### Run Locally

```bash
# Full Run
python -m packages.strategy_foundry.run_hourly

# Fast Mode (fewer candidates, fewer folds)
FAST_MODE=1 python -m packages.strategy_foundry.run_hourly
```

### Outputs

- `packages/strategy_foundry/results/runs/<timestamp>/`: detailed artifacts.
- `packages/strategy_foundry/results/champions/`: current best strategies.
- `packages/strategy_foundry/results/live_signal.json`: latest trading signal.

## Data

Data is fetched from Yahoo Finance (`^NSEI`, `^BSESN`) and cached in `data/cache/`.
