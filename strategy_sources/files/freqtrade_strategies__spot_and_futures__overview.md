# Freqtrade Strategies - Spot and Futures Overview

## Source
- **Repository**: https://github.com/freqtrade/freqtrade
- **Language**: Python
- **Type**: Cryptocurrency trading bot framework

## Key Strategies

### 1. MACD Momentum
- **Logic**: 
  - Buy when MACD crosses above signal line
  - Sell when MACD crosses below signal line
- **Parameters**:
  - Fast EMA period (default: 12)
  - Slow EMA period (default: 26)
  - Signal period (default: 9)
- **Use Case**: Trending markets
- **Performance**: Author-reported backtests show positive returns in trending conditions

### 2. Bollinger Bands Mean Reversion
- **Logic**:
  - Buy when price touches lower band
  - Sell when price touches upper band
- **Parameters**:
  - Period (default: 20)
  - Standard deviations (default: 2)
- **Use Case**: Range-bound markets
- **Performance**: Works well in mean-reverting conditions

### 3. RSI Divergence
- **Logic**: Detect RSI divergence with price
- **Use Case**: Trend reversal detection
- **Performance**: Works in specific market conditions

## India Market Adaptation Notes

### MACD Momentum Adaptation
- Use standard MACD parameters (12, 26, 9)
- Add volume confirmation
- Filter by Indian market hours
- Include transaction costs
- Use for NIFTY/BANKNIFTY futures

### Bollinger Bands Adaptation
- Use ATR-based bands for volatility adjustment
- Filter by volatility regime
- Add volume confirmation
- Include realistic costs

## Performance Disclaimer
⚠️ All performance numbers are author-reported backtests, NOT live performance. Use for research and inspiration only.

