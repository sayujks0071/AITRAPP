# Backtesting Methodology

## Assumptions
- **Slippage**: 2 bps per side
- **Costs**: Zerodha-like brokerage + Taxes
- **Execution**: Signal on Close -> Trade on Next Open

## Walk-Forward Analysis
We use Expanding Window Walk-Forward Analysis to avoid overfitting.
- 4 Folds
- Strategy must be profitable in >= 3 folds to be considered.

## Intraday Constraints
- Mandatory Flattening at 15:20 IST.
- No positions carried overnight.
- Max 1 trade per direction per day (optional).

## Data
Data is sourced from Yahoo Finance (`^NSEI`, `^BSESN`). Note that this data may have slight delays or gaps compared to tick-level broker data. We use it for trend/regime detection.
