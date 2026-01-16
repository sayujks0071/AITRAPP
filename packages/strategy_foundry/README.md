# Strategy Foundry

## Overview
The Strategy Foundry is an automated lab that generates, backtests, and selects aggressive intraday trading strategies for NIFTY and SENSEX. It runs hourly, evolving the "Champion" strategy based on Walk-Forward Analysis.

## Schedule
- **Runs:** Hourly (via GitHub Actions)
- **Market Hours:** 09:15 - 15:30 IST
- **Artifacts:** `packages/strategy_foundry/results/`

## Components
1. **Generator:** Creates random strategies using a grammar of blocks (Breakout, Trend, Reversion).
2. **Backtester:** Vectorized engine with realistic costs (Slippage, Spread Guard, Tax).
3. **Evaluator:** Walk-Forward Optimization (4 folds) to prevent overfitting.
4. **Ranker:** Selects champions based on Blended Score (Sharpe, Calmar, Stability).
5. **Publisher:** Emits `live_signal.json` if the champion is robust and market is open.

## Key Files
- `run_hourly.py`: Orchestrator.
- `configs/foundry.yaml`: Thresholds and settings.
- `results/live_signal.json`: Current trade signal (NO execution by default).

## Usage
Run manually:
```bash
export PYTHONPATH=$PYTHONPATH:.
python packages/strategy_foundry/run_hourly.py
```

Set `FAST_MODE=1` for quick checks (fewer candidates).
