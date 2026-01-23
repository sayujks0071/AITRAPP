# Backtesting Methodology

## Assumptions
- **Execution**: Signal at Close[i] -> Entry at Open[i+1].
- **Sizing**: 100% Equity (1x Leverage) or Fixed Fractional.
- **Costs**: Configured bps per side + slippage.

## Data
- Sources: Yahoo Finance (via `requests`) cached as CSV.
- Timeframes: 5m, 15m (Primary), 1D (Sanity).
- Session: 09:15 - 15:30 IST.

## Validation
To avoid overfitting:
1. **Folds**: Data is split into 4 chronological folds. Strategy must perform well across folds.
2. **Sanity**: Top candidates are checked on 1D data to ensure they aren't fragile to noise.
3. **Complexity Penalty**: Simpler strategies are preferred (implicit in grammar limits).

## Rejection Criteria
- Trades < 80 (5m) or 40 (15m).
- Max Drawdown > 30%.
- Profit Factor < 1.1.
- Positive Folds < 3/4.
