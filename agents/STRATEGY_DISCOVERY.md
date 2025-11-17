# Strategy Discovery Report

## Current State Analysis

### 1. Strategy Implementations

#### ORB (Opening Range Breakout)
**Location**: `packages/core/strategies/orb.py`

**Current Parameters**:
- `window_min`: 15 (opening range window)
- `breakout_confirmation_ticks`: 3 (confirmation requirement)
- `rr_min`: 1.8 (minimum risk-reward)
- `allowed_instruments`: ["NIFTY", "BANKNIFTY"]

**Missing Tunables** (from requirements):
- ❌ `atr_mult`: ATR buffer for breakout threshold
- ❌ `vol_z`: Volume z-score filter
- ❌ `widen_n`: Widening/narrowing guard threshold
- ❌ `cool_down`: Cooldown period between signals
- ❌ `confirm_candles`: Number of candles for confirmation

**Gaps**:
- No ATR-based breakout threshold (currently uses fixed %)
- No volume spike validation (has `volume_spike_mult` in YAML but not used)
- No widening/narrowing range guards
- No cooldown mechanism between signals

#### TrendPullback
**Location**: `packages/core/strategies/trend_pullback.py`

**Current Parameters**:
- `ema_fast`: 34
- `ema_slow`: 89
- `atr_period`: 14
- `pullback_atr_mult`: 0.5
- `rr_min`: 2.0
- `min_signal_gap_minutes`: 15 (hardcoded)

**Missing Tunables**:
- ❌ `rsi_band`: RSI filter bands (currently no RSI check)
- ❌ `fib`: Fibonacci retracement levels
- ❌ `min_adx`: ADX filter (mentioned in YAML but not implemented)

**Gaps**:
- No RSI filter
- No Fibonacci retracement support
- ADX mentioned in config but not used

#### OptionsRanker
**Location**: `packages/core/strategies/options_ranker.py`

**Current Parameters**:
- `strategy_type`: "DEBIT_SPREAD"
- `ivp_min`: 30
- `ivp_max`: 70
- `liquidity_score_min`: 0.7
- `max_spread_legs`: 2
- `rr_min`: 1.5

**Missing Tunables**:
- ❌ `dte`: Days to expiry range (min/max)
- ❌ `width`: Spread width in strikes
- ❌ `stop`: Stop loss % (currently hardcoded)
- ❌ `tp`: Take profit % (currently hardcoded)

**Gaps**:
- Placeholder option premium calculations
- No actual options chain integration
- No DTE filtering
- No spread width configuration

### 2. Crypto Strategies

**Status**: ❌ **NOT IMPLEMENTED**

**Required**:
- `CryptoMomentum`: lookback, keltner_mult, rsi_floor, vol_floor
- `CryptoPullback`: ema pairs, atr_pullback, cooldown, spread_guard

### 3. Backtest Engine

**Location**: `packages/core/backtest.py`

**Current Metrics**:
- ✅ Total return, return %
- ✅ Max drawdown
- ✅ Win rate, profit factor
- ✅ Avg win/loss
- ✅ Trade count

**Missing Metrics** (from requirements):
- ❌ Probabilistic Sharpe (bootstrap CI)
- ❌ Calmar ratio
- ❌ CVaR (Conditional Value at Risk)
- ❌ Turnover tracking
- ❌ White's Reality Check
- ❌ PBO (Probability of Backtest Overfit)

**Gaps**:
- No bootstrap validation
- No statistical significance testing
- No walk-forward implementation
- No regime-aware splitting

### 4. Risk Engine

**Location**: `packages/core/risk.py`

**Current Caps** (from configs):
- Indian PAPER: 0.30% per-trade, 1.0% heat, -1.50% daily stop
- Crypto PAPER: 0.25% per-trade, 1.0% heat, -1.25% daily stop
- Canary LIVE: 0.15% per-trade, 0.5% heat, -0.75% daily stop

**Status**: ✅ Caps are configurable and enforced

### 5. Cost Model

**Current**:
- Indian: ₹20/order + ₹2/option leg (from config)
- Crypto: 5-8 bps slippage per symbol (from config)
- Slippage: 5 bps (equity), configurable per symbol (crypto)

**Status**: ✅ Implemented in `PaperSimulator`

---

## Parameter Grids (Proposed)

### ORB (India)

```python
param_grid = {
    "window_min": [15],  # Fixed (core to strategy)
    "atr_mult": [0.8, 1.0, 1.2, 1.4],  # NEW: ATR buffer
    "vol_z": [0.5, 1.0, 1.5],  # NEW: Volume z-score threshold
    "widen_n": [0.1, 0.2, 0.3, 0.4],  # NEW: Range widening threshold
    "cool_down": [5, 10, 15],  # NEW: Minutes between signals
    "confirm_candles": [1, 2, 3],  # NEW: Confirmation candles
    "rr_min": [1.5, 1.8, 2.0, 2.2]
}
```

### TrendPullback (India)

```python
param_grid = {
    "ema_fast": [21, 34, 55],
    "ema_slow": [55, 89, 144],
    "rsi_band": [(45, 70), (40, 65)],  # NEW: (low, high) tuples
    "atr_pullback": [0.6, 0.8, 1.0, 1.2, 1.4],  # Rename from pullback_atr_mult
    "fib": [0.382, 0.5, 0.618],  # NEW: Fibonacci levels
    "rr_min": [1.8, 2.0, 2.5]
}
```

### OptionsRanker (India)

```python
param_grid = {
    "ivp": [(30, 70)],  # Range (min, max)
    "dte": [(3, 7), (5, 10), (7, 12)],  # NEW: Days to expiry range
    "width": [50, 100, 150, 200],  # NEW: Spread width in strikes
    "liq_score": [0.7],  # Fixed minimum
    "stop": [-35, -30, -25, -20],  # NEW: Stop loss %
    "tp": [+25, +35, +45, +50]  # NEW: Take profit %
}
```

### CryptoMomentum (Crypto - TO BE IMPLEMENTED)

```python
param_grid = {
    "lookback": [20, 30, 40, 50, 60],
    "keltner_mult": [1.5, 2.0, 2.5],
    "rsi_floor": [40, 45, 50],
    "vol_floor": [0.2, 0.3, 0.4]  # Quantile
}
```

### CryptoPullback (Crypto - TO BE IMPLEMENTED)

```python
param_grid = {
    "ema": [(50, 200)],  # Fast, slow pair
    "atr_pullback": [0.8, 1.0, 1.2, 1.4, 1.6],
    "cooldown": [10, 15, 20, 25, 30],  # Minutes
    "spread_guard": [50]  # Fixed (bps)
}
```

---

## Implementation Plan

### Phase 1: Enhance Existing Strategies
1. Add missing tunables to ORB (ATR, volume, widening guards)
2. Add RSI and Fib to TrendPullback
3. Add DTE, width, stop/tp to OptionsRanker

### Phase 2: Build Tuning Infrastructure
1. Create `scripts/tune_walkforward.py`
2. Implement walk-forward with expanding/anchored windows
3. Add bootstrap for Probabilistic Sharpe
4. Implement PBO calculation
5. Add White's Reality Check

### Phase 3: Crypto Strategies
1. Implement CryptoMomentum
2. Implement CryptoPullback
3. Integrate with crypto router

### Phase 4: Validation & Reporting
1. Run small validation (BTCUSDT + NIFTY)
2. Generate decision reports
3. Update configs
4. Add tests

---

## Next Steps

1. ✅ Discovery complete
2. ⏭️ Start with small parameter grid for ORB (add ATR/volume first)
3. ⏭️ Build walk-forward skeleton
4. ⏭️ Run validation on NIFTY only (faster iteration)


