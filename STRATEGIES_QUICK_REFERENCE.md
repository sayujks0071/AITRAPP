# Top 10 Nifty Strategies - Quick Reference Guide

**Date:** 2025-11-24  
**Status:** ✅ All Strategies Implemented and Ready

---

## 📋 Complete Strategy List

| Priority | Strategy Name | Type | Status | File |
|----------|--------------|------|--------|------|
| 1 | **OptionsRanker** | Options (Debit Spreads) | ✅ LIVE ENABLED | `options_ranker.py` |
| 2 | **SMAMomentum** | Momentum (MA Crossover) | ⚠️ Disabled | `sma_momentum.py` |
| 3 | **MACD** | Momentum (MACD Crossover) | ⚠️ Disabled | `macd_strategy.py` |
| 4 | **RSIMeanReversion** | Mean Reversion (RSI) | ⚠️ Disabled | `rsi_mean_reversion.py` |
| 5 | **BollingerBands** | Mean Reversion (BB) | ⚠️ Disabled | `bollinger_bands_strategy.py` |
| 6 | **Breakout** | Breakout (S/R) | ⚠️ Disabled | `breakout_strategy.py` |
| 7 | **VWAP** | Mean Reversion (VWAP) | ⚠️ Disabled | `vwap_strategy.py` |
| 8 | **MeanReversion** | Mean Reversion (ATR) | ⚠️ Disabled | `mean_reversion.py` |
| 9 | **TrendPullback** | Trend Following | ⚠️ Disabled | `trend_pullback.py` |
| 10 | **ORB** | Breakout (Opening Range) | ⚠️ Disabled | `orb.py` |

---

## 🚀 Quick Start Guide

### Current Status
- **Mode:** LIVE
- **Active Strategy:** OptionsRanker only
- **New Strategies:** All disabled for safety

### To Enable Strategies for Paper Testing

1. **Switch to Paper Mode:**
   ```yaml
   # In configs/app.yaml
   app:
     mode: PAPER  # Change from LIVE to PAPER
   ```

2. **Enable a Strategy:**
   ```yaml
   # In configs/app.yaml, find the strategy and change:
   - name: SMAMomentum
     enabled: true  # Change from false to true
   ```

3. **Start System:**
   ```bash
   make paper
   ```

### To Enable Strategies for Live Trading

⚠️ **Only after extensive paper testing!**

1. Keep `mode: LIVE` in config
2. Enable one strategy at a time
3. Monitor closely
4. Start with conservative position sizing

---

## 📊 Strategy Details

### 1. OptionsRanker (Priority 1) - LIVE
- **Type:** Options Debit Spreads
- **Instruments:** NIFTY
- **Status:** ✅ ENABLED in LIVE mode
- **Risk:** 0.30% per trade, 1 position max

### 2. SMAMomentum (Priority 2)
- **Type:** Moving Average Crossover
- **Logic:** Fast SMA (13) crosses Slow SMA (34)
- **Signals:** Golden Cross (LONG), Death Cross (SHORT)
- **Instruments:** NIFTY, BANKNIFTY

### 3. MACD (Priority 3)
- **Type:** MACD Crossover
- **Logic:** MACD line crosses Signal line
- **Signals:** Bullish crossover (LONG), Bearish crossover (SHORT)
- **Instruments:** NIFTY, BANKNIFTY

### 4. RSIMeanReversion (Priority 4)
- **Type:** RSI Mean Reversion
- **Logic:** RSI < 25 (oversold) or RSI > 75 (overbought)
- **Signals:** Oversold bounce (LONG), Overbought rejection (SHORT)
- **Instruments:** NIFTY, BANKNIFTY

### 5. BollingerBands (Priority 5)
- **Type:** Bollinger Bands Mean Reversion
- **Logic:** Price touches upper/lower bands
- **Signals:** Lower band touch (LONG), Upper band touch (SHORT)
- **Instruments:** NIFTY, BANKNIFTY

### 6. Breakout (Priority 6)
- **Type:** Support/Resistance Breakout
- **Logic:** Price breaks above resistance or below support
- **Signals:** Resistance breakout (LONG), Support breakdown (SHORT)
- **Instruments:** NIFTY, BANKNIFTY

### 7. VWAP (Priority 7)
- **Type:** VWAP Mean Reversion
- **Logic:** Price deviates from VWAP
- **Signals:** Below VWAP (LONG), Above VWAP (SHORT)
- **Instruments:** NIFTY, BANKNIFTY

### 8. MeanReversion (Priority 8)
- **Type:** ATR-Based Mean Reversion
- **Logic:** Price deviates from moving average with ATR bands
- **Signals:** Lower ATR band (LONG), Upper ATR band (SHORT)
- **Instruments:** NIFTY, BANKNIFTY

### 9. TrendPullback (Priority 9)
- **Type:** Trend Following with Pullbacks
- **Logic:** EMA trend + pullback to EMA
- **Signals:** Uptrend pullback (LONG), Downtrend pullback (SHORT)
- **Instruments:** All

### 10. ORB (Priority 10)
- **Type:** Opening Range Breakout
- **Logic:** Breakout from first 15 minutes range
- **Signals:** Above range high (LONG), Below range low (SHORT)
- **Instruments:** NIFTY, BANKNIFTY

---

## 🔧 Configuration Examples

### Enable SMAMomentum for Paper Testing
```yaml
strategies:
  - name: SMAMomentum
    enabled: true  # Enable this
    priority: 2
    params:
      sma_fast: 13
      sma_slow: 34
      instruments: [NIFTY, BANKNIFTY]
      max_positions: 1
```

### Enable Multiple Strategies
```yaml
strategies:
  - name: SMAMomentum
    enabled: true
    priority: 2
  - name: MACD
    enabled: true
    priority: 3
  - name: RSIMeanReversion
    enabled: true
    priority: 4
```

---

## 📈 Performance Monitoring

After enabling strategies, monitor:
- Signal generation rate
- Win rate
- Risk-reward ratios
- Drawdowns
- Position sizing

Use metrics endpoint:
```bash
curl http://localhost:8000/metrics | grep strategy
```

---

## 🛡️ Safety Reminders

1. **Always start in PAPER mode** for new strategies
2. **Enable one strategy at a time** for testing
3. **Monitor for 1-2 weeks** before considering LIVE
4. **Start with conservative position sizing** (max_positions: 1)
5. **Set tight risk limits** (per_trade_risk_pct: 0.25)

---

## ✅ Verification Checklist

Before enabling any strategy:
- [ ] Strategy file exists and is valid
- [ ] Strategy is registered in `__init__.py`
- [ ] Strategy is registered in `main.py`
- [ ] Strategy is configured in `configs/app.yaml`
- [ ] Python imports successfully
- [ ] Paper tested for sufficient time
- [ ] Performance metrics reviewed
- [ ] Risk limits set appropriately

---

## 🎯 Summary

**Total Strategies:** 10/10 ✅  
**Implementation:** Complete ✅  
**Registration:** Complete ✅  
**Configuration:** Complete ✅  
**Status:** Production Ready ✅

**Current State:**
- LIVE mode active
- OptionsRanker enabled
- All other strategies ready for paper testing

**Next Steps:**
1. Test strategies in PAPER mode
2. Review performance metrics
3. Gradually enable in LIVE mode after validation

---

**All systems ready! 🚀**

