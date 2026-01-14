# Strategy Foundry

A self-generating strategy lab that runs hourly to discover, backtest, and promote trading strategies for NIFTY and SENSEX.

## Architecture

- **Data**: Fetches daily OHLC from Yahoo Finance, cached as CSV.
- **Factory**: Generates random strategies using a grammar of indicators (RSI, ADX, EMA, Supertrend).
- **Backtest**: Vectorized engine with walk-forward evaluation (3 folds).
- **Selection**: Ranks strategies by Sharpe, Calmar, and Stability. Promotes champions if they beat the incumbent.
- **Live**: Publishes a JSON signal file (`live_signal.json`) if the market is open and a valid champion exists.

## Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run (Default mode N=50)
python packages/strategy_foundry/run_hourly.py

# Run Fast Mode (N=10, 2 folds)
FAST_MODE=1 python packages/strategy_foundry/run_hourly.py
```

## Outputs

Results are stored in `packages/strategy_foundry/results/`:
- `runs/<timestamp>/`: Artifacts of each run (candidates, rankings).
- `champions/`: JSON files of current and past champions.
- `live_signal.json`: The latest trading signal (if market open).
- `leaderboard.md`: History of top performers.
