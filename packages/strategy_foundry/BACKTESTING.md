# Backtesting Methodology

## Assumptions
- **Execution**: Signals calculated on Bar Close, executed on Next Open.
- **Slippage**: 5bps default + Commission.
- **Data**: Yahoo Finance 5m/15m data (Top of book not available, assumed filled at Open).

## Validation
1. **Walk-Forward**: 4 folds OOS evaluation.
2. **Sanity**:
   - Minimum trade count (30)
   - Max Drawdown < 35%
   - Profit Factor > 1.1
3. **Daily Overlay**: Strategy must not fail catastrophically on 1D timeframe.

## Limitations
- Intraday data history from Yahoo is limited (60 days).
- No bid-ask spread modeling (Slippage proxy used).
- Market impact not modeled.
