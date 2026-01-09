# Backtesting Methodology

## Data Strategy
*   **Timeframes**: 5m and 15m (Primary), 1D (Sanity).
*   **Sources**: Core provider (if available) -> Yahoo Finance (Lightweight downloader) -> Cache.
*   **Timezone**: Asia/Kolkata. Intraday data is filtered to 09:15 - 15:30 IST.

## Execution Model
*   **Entries**: Signal calculated on bar close; entry on next bar Open.
*   **Exits**:
    *   Stop Loss / Take Profit: Checked against High/Low of current bar (intra-bar).
    *   EOD Exit: Forced flat at 15:25 IST.
    *   Time Exit: Max bars held.
*   **Costs**:
    *   Slippage: 5 bps per side.
    *   Commission: 3 bps per side.
    *   Flat Fee: 20 INR per order.
    *   Spread Guard: Configurable penalty for choppy markets.

## Validation
*   **Walk-Forward**: 4 folds (expanding window train, sliding test).
*   **Sanity Checks**:
    *   Minimum Trades: 80 (5m), 40 (15m).
    *   Max Drawdown: < 30%.
    *   Profit Factor: > 1.1.
    *   Positive Folds: 3/4.
    *   Intraday Sanity: "Late Day Dependence" check (reject if >50% profit in last 30 mins).
    *   Daily Sanity Overlay: Top candidates checked on 1D timeframe for catastrophic failure.

## Ranking
Candidates are ranked using a weighted score:
*   Sharpe (25%)
*   Calmar (25%)
*   Net Return (20%)
*   Stability (15%)
*   Low Turnover (10%)
*   Sanity Bonus (5%)

A **Blended Score** (60% 15m + 40% 5m) is used for final champion selection if both timeframes are available.
