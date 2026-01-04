# Backtesting Methodology

## Engine Assumptions

1.  **Timeframe**: Daily (1D).
2.  **Execution**:
    *   **Entry**: Market Open of the bar *after* the signal is generated.
    *   **Exit**: Market Open of the bar *after* exit signal, OR Intraday Stop Loss.
3.  **Costs**:
    *   Slippage: 5 bps per side.
    *   Transaction Costs: 10 bps per side (approx all-in).

## Walk-Forward Evaluation

To prevent overfitting, we use Walk-Forward Evaluation (WFE):

1.  Data is split into `N` folds (default 4).
2.  Each fold is evaluated independently (Out-of-Sample validation).
3.  A strategy must perform consistently across folds to be considered.

## Scoring & Ranking

Composite Score calculated as:

*   30% Sharpe Ratio (Risk-adjusted return)
*   25% Calmar Ratio (Return / Max Drawdown)
*   20% CAGR (Absolute return)
*   15% Stability (Low dispersion of Sharpe across folds)

Strategies with Max Drawdown > 35% or < 30 trades are rejected.
