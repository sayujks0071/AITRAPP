# bt Framework - Strategy Overview

## Source
- **Repository**: https://github.com/pmorissette/bt
- **Language**: Python
- **Type**: Backtesting framework with strategy building blocks

## Key Strategies

### 1. Mean Reversion Strategy
- **Logic**: Buy when price deviates below moving average, sell when above
- **Parameters**: 
  - Lookback period (default: 20)
  - Deviation threshold (default: 2 standard deviations)
- **Use Case**: Range-bound markets, liquid stocks
- **Performance**: Author-reported backtests show positive returns in mean-reverting regimes

### 2. Momentum Strategy
- **Logic**: Buy when price crosses above moving average, sell when below
- **Parameters**:
  - Fast MA period (default: 10)
  - Slow MA period (default: 30)
- **Use Case**: Trending markets
- **Performance**: Works well in trending conditions

### 3. Portfolio Allocation Strategies
- **Equal Weight**: Equal allocation across assets
- **Risk Parity**: Allocation based on risk contribution
- **Use Case**: Multi-asset portfolios

## India Market Adaptation Notes

### Mean Reversion Adaptation
- Use ATR-based bands instead of fixed standard deviations
- Filter by volatility regime (avoid high volatility periods)
- Respect Indian market hours (09:15-15:30 IST)
- Include realistic transaction costs (12-15 bps round-trip)

### Momentum Adaptation
- Use EMA instead of SMA for faster response
- Add volume confirmation
- Filter by liquidity (min turnover threshold)
- Include slippage (5-10 bps)

## Performance Disclaimer
⚠️ All performance numbers are author-reported backtests, NOT live performance. Use for research and inspiration only.

