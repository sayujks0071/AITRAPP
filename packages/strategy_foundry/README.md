# Strategy Foundry

Autonomous strategy research lab that runs hourly to generate, test, and select trading strategies for NIFTY and SENSEX.

## Architecture

- **Hybrid Design**: Reuses `packages/core` primitives (indicators, market hours) via adapters.
- **Self-Generating**: Uses a grammar to compose Trend, Mean Reversion, and Filter blocks.
- **Walk-Forward Validation**: Strategies are validated on out-of-sample data folds.
- **Champion Selection**: The best strategy (Champion) is promoted based on a composite score (Sharpe, Calmar, CAGR, Stability).
- **Safe Output**: Produces a JSON artifact (`live_signal_NIFTY.json`). **No real orders are placed.**

## Structure

- `data/`: Data loading (Yahoo Finance) and caching.
- `factory/`: Strategy grammar and random generator.
- `backtest/`: Vectorized backtest engine and walk-forward evaluator.
- `selection/`: Ranking and champion management.
- `live/`: Signal generation for the current champion.
- `results/`: Run artifacts and leaderboards.

## Usage

### Run Locally (Fast Mode)

```bash
export FAST_MODE=1
python packages/strategy_foundry/run_hourly.py
```

### Run Full

```bash
export FAST_MODE=0
python packages/strategy_foundry/run_hourly.py
```

## CI/CD

The module runs hourly via GitHub Actions (`.github/workflows/strategy_foundry_hourly.yml`).
PRs trigger a FAST_MODE run to verify integrity.
