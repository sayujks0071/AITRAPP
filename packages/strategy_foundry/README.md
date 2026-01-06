# Strategy Foundry

## Overview
Self-generating strategy lab that runs hourly to discover, backtest, and select trading strategies for NIFTY/SENSEX.

## Architecture
- **Data**: Downloads daily OHLCV from Yahoo Finance (cached).
- **Generator**: Creates random strategies using a grammar of indicators (EMA, RSI, Supertrend, etc.) and risk rules.
- **Backtest**: Vectorized engine with walk-forward validation (Out-of-Sample testing).
- **Selection**: Ranks strategies by Sharpe, Calmar, and Stability. Promotes "Champions".
- **Live**: Publishes `live_signal.json` if market is open and champion is robust.

## Usage

### Local Run
```bash
# Fast mode (fewer candidates, faster run)
FAST_MODE=1 python -m packages.strategy_foundry.run_hourly

# Full mode
python -m packages.strategy_foundry.run_hourly
```

### Outputs
Artifacts are stored in `packages/strategy_foundry/results/`:
- `runs/<timestamp>/`: Candidates and metrics.
- `champions/`: Current champion JSON.
- `live_signal.json`: Current live signal (if eligible).

## Dependencies
- `pandas`, `numpy`, `httpx`
- No heavy ML libraries.
