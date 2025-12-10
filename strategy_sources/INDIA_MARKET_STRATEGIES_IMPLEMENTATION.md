# India Market Strategies Implementation Summary

**Date:** 2025-01-27  
**Status:** ✅ Complete - Ready for Paper Trading

---

## Overview

This document summarizes the implementation of India-market-ready trading strategies based on open-source strategy designs from `strategy_sources/`. All strategies are wired **ONLY to paper trading mode** for safe research and testing.

---

## Implemented Strategies

### 1. ✅ SMA Momentum Strategy (vectorbt-inspired)

**File:** `packages/core/strategies/sma_momentum.py`  
**Status:** Already existed, verified and integrated

**Design Source:** vectorbt SMA crossover examples  
**Adaptation:**
- Fast SMA (13) / Slow SMA (34) crossover
- ATR-based stops and targets
- Volume confirmation
- Indian market hours (09:15-15:30 IST)
- Realistic transaction costs accounted for

**Key Features:**
- Golden Cross (LONG) and Death Cross (SHORT) signals
- ATR-based risk management
- Volume filter to avoid false signals
- Configurable parameters for different market conditions

---

### 2. ✅ Mean Reversion Strategy (bt-inspired)

**File:** `packages/core/strategies/mean_reversion.py`  
**Status:** ✅ Newly implemented

**Design Source:** bt framework mean reversion examples  
**Adaptation:**
- ATR-based bands instead of fixed standard deviations
- Volatility regime filtering (avoids high volatility periods)
- Volume confirmation
- Indian market hours and transaction costs

**Key Features:**
- Buy when price touches lower ATR band (oversold)
- Sell when price touches upper ATR band (overbought)
- Mean reversion targets (back to moving average)
- Volatility filter to avoid trading in chaotic markets
- Configurable MA type (SMA or EMA)

**Parameters:**
- `ma_period`: 20 (default)
- `ma_type`: "SMA" or "EMA"
- `atr_band_mult`: 2.0 (ATR multiplier for bands)
- `atr_stop_mult`: 1.5 (ATR multiplier for stop-loss)
- `max_volatility_atr_mult`: 3.0 (volatility filter)

---

### 3. ✅ RSI Mean Reversion Strategy (vectorbt-inspired)

**File:** `packages/core/strategies/rsi_mean_reversion.py`  
**Status:** ✅ Newly implemented

**Design Source:** vectorbt RSI mean reversion examples  
**Adaptation:**
- Tighter RSI thresholds (25/75) for Indian markets (vs 30/70 standard)
- Volume confirmation
- Liquidity filtering
- Indian market hours and transaction costs

**Key Features:**
- Buy when RSI < 25 (oversold)
- Sell when RSI > 75 (overbought)
- RSI bounce confirmation (waits for RSI recovery/rejection)
- ATR-based stops and targets
- Liquidity filter (minimum turnover threshold)

**Parameters:**
- `rsi_period`: 14 (default)
- `oversold_threshold`: 25 (tighter for Indian markets)
- `overbought_threshold`: 75 (tighter for Indian markets)
- `min_liquidity_turnover`: 10,000,000 (₹1 crore)

---

## India Market Adaptations

All strategies include the following India-market-specific adaptations:

### 1. Market Hours
- **Cash Market:** 09:15 - 15:30 IST
- **F&O Market:** 09:15 - 15:30 IST
- **EOD Square-Off:** 15:25 IST (all positions flat)
- Strategies validate market hours before generating signals

### 2. Transaction Costs
Cost model reference: `configs/costs/india_equities.yaml`

**Cost Components:**
- Slippage: 5 bps (liquid instruments)
- Brokerage: ₹20 per order
- Exchange charges: 3 bps
- STT: 1 bps
- GST: 1.8 bps (on brokerage + exchange charges)
- Stamp duty: 0.003 bps
- SEBI charges: 0.0005 bps

**Total Round-Trip Cost:** ~12-15 bps for liquid instruments

**How Strategies Account for Costs:**
- Confidence levels set to moderate (0.65-0.70) to account for costs
- Minimum risk-reward ratios (1.5-2.0) ensure costs are covered
- Volume and liquidity filters reduce impact costs
- ATR-based stops minimize unnecessary trades

### 3. Lot Sizes
- **NIFTY Futures:** 25
- **BANKNIFTY Futures:** 15
- **FINNIFTY Futures:** 40
- Strategies respect lot sizes through position sizing

### 4. Liquidity Requirements
- Minimum turnover filters (₹1 crore for RSI strategy)
- Volume confirmation to avoid illiquid instruments
- Liquidity scoring in signal ranking

### 5. Volatility Considerations
- ATR-based stops (better for Indian market volatility)
- Volatility regime filtering (mean reversion strategy)
- Dynamic stop-loss based on market conditions

---

## Configuration

### Paper Trading Config

**File:** `configs/kite_paper.yaml`

**Key Settings:**
- `app.mode: PAPER` - Ensures all strategies run in paper trading mode
- Risk limits: 0.25% per trade, 1.0% portfolio heat, -2.5% daily stop
- Market hours: 09:15-15:30 IST
- EOD square-off: 15:25 IST

**Strategy Configuration:**
All new strategies are enabled with conservative parameters:
- Priority: 2-3 (lower than ORB/TrendPullback)
- Max positions: 2 per strategy
- Risk-reward: 1.5 minimum
- Volume confirmation: Enabled
- Liquidity filters: Enabled

---

## Integration Points

### 1. Strategy Registration

**File:** `packages/core/strategies/__init__.py`
```python
from packages.core.strategies.mean_reversion import MeanReversionStrategy
from packages.core.strategies.rsi_mean_reversion import RSIMeanReversionStrategy
```

### 2. Strategy Instantiation

**File:** `apps/api/main.py`
- Added imports for new strategies
- Added instantiation blocks in strategy loading loop
- Strategies are registered in `strategy_registry` for meta-strategies

### 3. Strategy Context

All strategies use `StrategyContext` which provides:
- Market data (ticks, bars)
- Portfolio state
- Regime and event snapshots
- Instrument information

---

## Usage

### Starting Paper Trading Session

1. **Set Configuration:**
   ```bash
   cp configs/kite_paper.yaml configs/app.yaml
   export APP_MODE=PAPER
   ```

2. **Start System:**
   ```bash
   make paper
   ```

3. **Monitor Strategies:**
   - Strategies will start scanning at 09:15 IST
   - Signals generated based on market conditions
   - All trades executed in paper trading mode (no real money)

### Strategy Selection

Strategies are prioritized:
1. **Priority 1:** ORB, TrendPullback (existing, proven)
2. **Priority 2:** SMAMomentum (momentum-based)
3. **Priority 3:** MeanReversion, RSIMeanReversion (mean reversion)

Lower priority strategies run after higher priority ones in each scan cycle.

---

## Performance Expectations

⚠️ **Important Disclaimers:**

1. **All performance numbers from source repositories are:**
   - Author-reported backtest results
   - NOT live or guaranteed performance
   - Strictly for research and inspiration

2. **Indian Market Differences:**
   - Higher transaction costs than US markets
   - Different market microstructure
   - Different volatility patterns
   - Different liquidity characteristics

3. **Paper Trading Only:**
   - All strategies are wired to PAPER mode
   - No live trading until extensive validation
   - Use for research, backtesting, and strategy development

---

## Next Steps

### Immediate (Completed)
- ✅ Mean Reversion Strategy
- ✅ RSI Mean Reversion Strategy
- ✅ Paper trading configuration
- ✅ Strategy registration and integration

### Future Enhancements (Research Phase)
- Portfolio Optimization Strategy (PyPortfolioOpt-inspired)
  - Requires different architecture (multi-instrument allocation)
  - Deferred for future implementation
- Multi-timeframe strategies (NostalgiaForInfinity-inspired)
- RL-based strategies (FinRL-inspired)
  - Requires retraining on Indian market data
  - Significant adaptation needed

---

## Files Created/Modified

### New Files
1. `packages/core/strategies/mean_reversion.py` - Mean Reversion Strategy
2. `packages/core/strategies/rsi_mean_reversion.py` - RSI Mean Reversion Strategy
3. `configs/kite_paper.yaml` - Paper trading configuration
4. `strategy_sources/INDIA_MARKET_STRATEGIES_IMPLEMENTATION.md` - This document

### Modified Files
1. `packages/core/strategies/__init__.py` - Added strategy exports
2. `apps/api/main.py` - Added strategy imports and instantiation

---

## Testing Recommendations

1. **Paper Trading Validation:**
   - Run strategies in paper mode for 1-2 weeks
   - Monitor signal quality and execution
   - Validate cost assumptions
   - Check risk management

2. **Backtesting:**
   - Use historical data to validate strategies
   - Test different parameter combinations
   - Validate transaction cost assumptions
   - Check performance across different market regimes

3. **Parameter Tuning:**
   - Adjust ATR multipliers based on market conditions
   - Fine-tune RSI thresholds for Indian markets
   - Optimize volume confirmation thresholds
   - Test different MA periods

---

## Safety Features

1. **Paper Trading Only:**
   - All strategies configured for PAPER mode
   - No risk of live trading until explicitly enabled

2. **Risk Management:**
   - Position limits (max 2 per strategy)
   - Portfolio heat limits (1.0%)
   - Daily loss stops (-2.5%)
   - ATR-based stops

3. **Market Hours Validation:**
   - Strategies only trade during market hours
   - EOD square-off enforced

4. **Liquidity Filters:**
   - Minimum turnover requirements
   - Volume confirmation
   - Avoids illiquid instruments

---

## Summary

✅ **Three India-market-ready strategies implemented:**
1. SMAMomentum (vectorbt-inspired) - Already existed
2. MeanReversion (bt-inspired) - ✅ New
3. RSIMeanReversion (vectorbt-inspired) - ✅ New

✅ **All strategies:**
- Adapted for Indian markets (NSE cash + F&O)
- Include realistic transaction costs
- Respect market hours and lot sizes
- Wired to paper trading mode only
- Integrated into AITRAPP architecture

✅ **Ready for:**
- Paper trading research
- Strategy validation
- Parameter tuning
- Performance analysis

**Status: 🟢 READY FOR PAPER TRADING**

