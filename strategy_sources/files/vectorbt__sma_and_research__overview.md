# vectorbt - SMA and Research Strategies Overview

## Source
- **Repository**: https://github.com/polakowo/vectorbt
- **Language**: Python
- **Type**: Vectorized backtesting framework

## Key Strategies

### 1. SMA Crossover Strategy
- **Logic**: 
  - Buy when fast SMA crosses above slow SMA
  - Sell when fast SMA crosses below slow SMA
- **Parameters**:
  - Fast SMA period (default: 10)
  - Slow SMA period (default: 30)
- **Use Case**: Trending markets, liquid indices
- **Performance**: Author-reported backtests show positive returns in trending conditions

### 2. RSI Mean Reversion
- **Logic**:
  - Buy when RSI < 30 (oversold)
  - Sell when RSI > 70 (overbought)
- **Parameters**:
  - RSI period (default: 14)
  - Oversold threshold (default: 30)
  - Overbought threshold (default: 70)
- **Use Case**: Range-bound markets
- **Performance**: Works well in mean-reverting conditions

### 3. Portfolio Optimization
- **Logic**: Optimize portfolio weights using mean-variance optimization
- **Parameters**:
  - Risk-free rate
  - Covariance estimation method
- **Use Case**: Multi-asset portfolios

## India Market Adaptation Notes

### SMA Crossover Adaptation
- Use 5s/1m bars for intraday trading
- Fast SMA: 9-13 periods
- Slow SMA: 21-34 periods
- Add volume confirmation
- Filter by Indian market hours
- Include transaction costs (12-15 bps)

### RSI Mean Reversion Adaptation
- Adjust RSI period to 14 (standard)
- Use tighter thresholds for Indian markets (25/75 instead of 30/70)
- Add volume confirmation
- Filter by liquidity
- Include realistic costs

## Performance Disclaimer
⚠️ All performance numbers are author-reported backtests, NOT live performance. Use for research and inspiration only.

