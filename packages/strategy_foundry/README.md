# Strategy Foundry

A self-generating strategy lab that runs hourly to discover, evaluate, and rank trading strategies for NIFTY/SENSEX.

## Architecture

- **Data**: Daily OHLCV from Yahoo Finance (cached).
- **Factory**: Generates random strategies using a grammar of indicators (Trend, Mean Reversion).
- **Backtest**: Vectorized engine for fast evaluation.
- **Evaluation**: Walk-Forward Analysis (WFA) to prevent overfitting.
- **Ranking**: Composite score (Sharpe, Calmar, Stability).
- **Live**: Publishes `live_signal.json` (No execution, signal only).

## Usage

### Local Run

```bash
# Full run
python -m packages.strategy_foundry.run_hourly

# Fast mode (fewer candidates)
FAST_MODE=1 python -m packages.strategy_foundry.run_hourly
```

### Outputs

Results are stored in `packages/strategy_foundry/results/`:
- `runs/`: Detailed logs and metrics.
- `champions/`: Promoted strategy configurations.
- `leaderboard.md`: Current top strategies.
- `live_signal.json`: Latest actionable signal.

## CI/CD

Runs hourly via GitHub Actions.
