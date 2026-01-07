# Backtesting Methodology

## Data Sources

1. **Core Data Provider**: First preference (if available).
2. **Yahoo Finance Fallback**: Uses `requests` to fetch `^NSEI` (NIFTY) and `^BSESN` (SENSEX).
   - Caches to CSV in `packages/strategy_foundry/data/cache/`.
   - Auto-refreshes if cache is stale (1h for intraday, 12h for daily).

## Strategy Generation

Strategies are composed of:
- **Entry**: Breakout (Donchian, ORB), Trend (EMA Cross), Mean Reversion (RSI).
- **Exit**: Target/Stop (RR), Trailing Stop (ATR), EOD (Time).
- **Risk**: Fixed % or ATR-based stop.
- **Filters**: Trend filter (Higher TF EMA), Time filter (No trade first 30m).

## Walk-Forward Validation

To ensure robustness, we use Walk-Forward Analysis:
- **Train**: Optimization window (implicit in generation selection).
- **Test**: Out-of-Sample (OOS) window immediately following train.
- **Folds**: 4 folds by default (expanding window).

## Sanity Checks

1. **Daily Sanity**: Top candidates are run on 1D data.
   - Rejection if Sharpe < -0.2 or MaxDD > 45%.
   - Ensures strategy doesn't blow up on longer horizons.
2. **Intraday constraints**:
   - Mandatory flattening at 15:25 IST.
   - Spread guard costs applied.

## Ranking

Strategies are ranked by a weighted score:
- 25% Sharpe
- 25% Calmar
- 20% CAGR
- 15% Stability (Positive Folds)
- 10% Efficiency (Turnover/Profit Factor)

Champions are promoted only if they significantly outperform the incumbent.
