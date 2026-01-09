# Strategy Foundry

Self-generating strategy lab that runs hourly to discover, backtest, and select trading strategies for NIFTY/SENSEX.

## Architecture

- **Data**: Downloads daily OHLCV from Yahoo Finance (cached).
- **Factory**: Generates strategies using a grammar (Trend, Mean Reversion, Filters).
- **Backtest**: Vectorized engine for fast evaluation. Uses Walk-Forward Analysis.
- **Selection**: Ranks by composite score (Sharpe, Calmar, CAGR, Stability).
- **Live**: Publishes `live_signal.json` if market is open and champion is eligible.

## Usage

### Local Run
```bash
# Fast mode (fewer candidates)
python packages/strategy_foundry/run_hourly.py --fast

# Full mode
python packages/strategy_foundry/run_hourly.py
```

### Outputs
Artifacts are stored in `packages/strategy_foundry/results/`.
- `runs/<timestamp>/candidates.csv`: All candidates from the run.
- `champions/current.json`: The current champion strategy.
- `live_signal.json`: The latest trading signal (if market open).
- `leaderboard.md`: Top strategies.

## Deployment

The system runs hourly via GitHub Actions.
To enable live consumption of signals, set `ENABLE_LIVE=true` in the core system and ensure `approvals/ALLOW_LIVE.txt` exists.
