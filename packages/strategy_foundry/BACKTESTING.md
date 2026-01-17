# Backtesting Methodology

## Assumptions

- **Timeframe**: Daily (1D).
- **Execution**: Signals generated at Close of Day T are executed at Open of Day T+1.
- **Price**: Yahoo Finance adjusted data (conceptually, though we use raw Close for signals usually).
- **Costs**:
  - Slippage: 2 bps per side.
  - Commission/Tax: 3.5 bps per side (Proxy for Futures/Options cost on Index).
  - Total round-trip drag: ~11 bps.

## Walk-Forward Evaluation

To avoid overfitting, we use Out-Of-Sample (OOS) testing.
- The dataset is split (e.g., last 30% is OOS).
- Candidates are ranked solely on their OOS performance.
- We assume that random generation provides enough "In-Sample" variation that checking OOS performance is sufficient validation.

## Metrics

- **Sharpe Ratio**: Annualized (Risk-free rate = 0).
- **Calmar Ratio**: CAGR / MaxDrawdown.
- **CAGR**: Compound Annual Growth Rate.
- **Stability**: Win Rate / Profit Factor proxy.

## Caveats

- **Look-ahead Bias**: We use `shift(1)` for signals to ensure no look-ahead. Execution at Next Open ensures realism.
- **Survivorship Bias**: Yahoo Finance data for indices is generally stable, but constituent changes are not modeled (we trade the Index proxy).
- **Data Quality**: Yahoo Finance data may have gaps or errors. We filter NaNs but do not perform deep cleaning.
