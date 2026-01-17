# Strategy Foundry

A self-generating strategy lab that runs hourly to discover, backtest, and promote trading strategies for NIFTY/SENSEX.

## Architecture

- **Data**: Downloads daily OHLCV from Yahoo Finance (^NSEI, ^BSESN) via `requests`. Caches to CSV.
- **Factory**: Generates random strategies using a bounded grammar (Trend, Mean Reversion, Filters, Risk).
- **Backtest**: Daily timeframe, next-bar open execution. Uses `packages.core.indicators` (via adapters) for calculations.
- **Selection**: Walk-forward evaluation (OOS metrics). Ranks by Sharpe, Calmar, CAGR.
- **Live**: Publishes `live_signal.json` (No real orders).

## Usage

### Local Run

```bash
# Full mode
python -m packages.strategy_foundry.run_hourly

# Fast mode (fewer candidates)
FAST_MODE=1 python -m packages.strategy_foundry.run_hourly
```

### Outputs

Results are stored in `packages/strategy_foundry/results/`:
- `runs/<timestamp>/`: Artifacts for each run.
- `champions/`: JSON files of promoted champions.
- `leaderboard.csv`: Historical performance of candidates.
- `leaderboard.md`: Top 20 leaderboard.
- `live_signal.json`: Current trade signal (if market open).

## CI/CD

Runs hourly via GitHub Actions to continuously explore the parameter space.
