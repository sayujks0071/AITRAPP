# Backtesting Methodology

## Data Strategy
-   **Primary**: 5m and 15m intraday bars.
-   **Sanity**: 1D bars for checking major trend alignment and structural breaks.
-   **Source**: Yahoo Finance (cached locally).
-   **Timezone**: Normalized to Asia/Kolkata (IST).

## Engine
-   **Type**: Hybrid.
    -   **Signal Generation**: Vectorized (Pandas/NumPy) for speed.
    -   **Execution**: Event-driven loop to strictly enforce intraday constraints (time stops, EOD exits).
-   **Execution Price**: Next Open (after signal).
-   **Costs**:
    -   Slippage: 5 bps per side.
    -   Commission: 3 bps per side.

## Validation
-   **Walk-Forward**: Data is split into 4 folds (default).
-   **Ranking**: Strategies are ranked on Out-of-Sample (OOS) performance only.
-   **Overfitting Guards**:
    -   Must have positive expectancy in 3/4 folds.
    -   Max Drawdown < 30%.
    -   Profit Factor > 1.1.
