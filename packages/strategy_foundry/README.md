# Strategy Foundry

A self-generating strategy lab that runs hourly to discover, backtest, and select trading strategies for Indian markets (NIFTY/SENSEX).

## Features
- **Daily Timeframe**: Focus on 1D swing strategies.
- **Self-Generating**: Uses a grammar to generate random strategy candidates (Trend, Mean Reversion, Volatility).
- **Walk-Forward Evaluation**: Validates strategies on Out-of-Sample (OOS) data to prevent overfitting.
- **Champion Selection**: Automatically promotes strategies that beat the incumbent score.
- **Paper-First**: Publishes signals to a JSON file (`results/live_signal.json`) without executing live orders.
- **Zero Heavy Deps**: Uses `requests` and `pandas` (no `yfinance` library).

## Usage

### Local Run
```bash
python packages/strategy_foundry/run_hourly.py
```

### Fast Mode (for CI/Testing)
```bash
FAST_MODE=1 python packages/strategy_foundry/run_hourly.py
```

## Directory Structure
- `data/`: Data loader and cache.
- `factory/`: Strategy grammar and generator.
- `backtest/`: Engine and metrics.
- `selection/`: Ranking and champion store.
- `live/`: Signal publisher.
- `results/`: Run artifacts and signals.

## CI/CD
Runs hourly via GitHub Actions to continuously explore the strategy space.
