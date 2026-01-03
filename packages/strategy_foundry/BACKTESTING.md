# Backtesting Methodology

## Data Sources

- Primary: Yahoo Finance (Lightweight, Cached)
- Fallback: Core Historical Data (if available)

## Strategy Generation

We use a grammar-based generation approach:
- **Entries**: EMA Cross, Donchian Breakout, RSI Reversion.
- **Exits**: ATR Stop, Profit Target, Time Stop, End-of-Day (Hard Close).
- **Filters**: ADX (Trend Strength).

## Evaluation

Strategies are evaluated using Walk-Forward Analysis (Train/Test split).
- **Metric**: Sharpe Ratio, Net Return, Max Drawdown.
- **Robustness**: Performance consistency across 15m and 5m timeframes.

## Selection

The top strategy ("Champion") is selected based on a blended score of 15m and 5m performance.
Strict gates are applied:
- Minimum Score
- Max Drawdown limit
- Minimum trade count

## Intraday Constraints

- All positions must be closed by 15:25 IST.
- No overnight risk.
