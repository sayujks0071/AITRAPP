# Backtesting Methodology

## Engine
- **Type**: Vectorized daily resolution.
- **Execution**: Trades are executed at the **Open** of the day following the signal.
  - Signal generated at Close(T).
  - Trade executed at Open(T+1).
- **Costs**:
  - Slippage: 5 bps per side.
  - All-in Cost (Brokerage + Taxes): 3 bps per side.
  - Total: 8 bps per side (0.16% round trip).

## Walk-Forward Validation
To prevent overfitting, we use Expanding Window Walk-Forward Analysis:
- Data is split into N folds.
- **Train**: Growing window.
- **Test**: Fixed window following Train.
- We report metrics ONLY on the concatenated Out-of-Sample (Test) periods.

## Ranking
Composite Score Weights:
- **Sharpe Ratio**: 30%
- **Calmar Ratio**: 25%
- **CAGR**: 20%
- **Stability**: 15%
- **Turnover**: Implicit penalty via trade counts and costs.

## Sanity Checks
Strategies are rejected if:
- Trades < 30 (10 in Fast Mode).
- Max Drawdown > 35%.
- Consistency: Fewer than 2 positive OOS folds.
