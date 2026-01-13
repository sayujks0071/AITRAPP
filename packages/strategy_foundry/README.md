# Strategy Foundry

Self-generating strategy lab.

## Architecture

- **Data**: Yahoo Finance (Daily). Cached in `data/cache/`.
- **Generation**: Random composition of Trend, Mean Reversion, and Risk blocks.
- **Backtest**: Daily timeframe, executing at Next Open.
- **Evaluation**: Walk-Forward (expanding window).
- **Live**: Publishes `live_signal.json`. No automatic execution.

## Usage

### Run Locally
```bash
# Fast mode (fewer candidates)
python packages/strategy_foundry/run_hourly.py --fast

# Full mode
python packages/strategy_foundry/run_hourly.py
```

### CI
Runs hourly via GitHub Actions.

## Modules

- `data`: Loading and caching.
- `factory`: Strategy grammar and generation.
- `backtest`: Engine and metrics.
- `selection`: Ranking and promotion.
- `live`: Signal publishing.
