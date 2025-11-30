# 24-Hour Paper Trading Test Guide

**Date:** 2025-11-24  
**Mode:** PAPER  
**Status:** ✅ All 12 Strategies Enabled

---

## ✅ Configuration Applied

### Mode Change
- **Previous:** LIVE
- **Current:** PAPER ✅

### Strategies Enabled (12 Total)

1. ✅ **OptionsRanker** (Priority 1)
2. ✅ **SMAMomentum** (Priority 2) - NEW
3. ✅ **MACD** (Priority 3) - NEW
4. ✅ **RSIMeanReversion** (Priority 4) - NEW
5. ✅ **BollingerBands** (Priority 5) - NEW
6. ✅ **Breakout** (Priority 6) - NEW
7. ✅ **VWAP** (Priority 7) - NEW
8. ✅ **MeanReversion** (Priority 8) - NEW
9. ✅ **TrendPullback** (Priority 9)
10. ✅ **ORB** (Priority 10)

---

## 🚀 Restart Instructions

### Option 1: Using Makefile (Recommended)

```bash
# Stop current system
docker-compose down

# Start in paper mode
make paper
```

### Option 2: Manual Restart

```bash
# Stop current backend
docker-compose restart backend

# Or if running directly:
# Find and kill the process
ps aux | grep uvicorn | grep -v grep | awk '{print $2}' | xargs kill

# Start fresh
make paper
```

### Option 3: Docker Compose Restart

```bash
cd /Users/mac/CRYPTO/AITRAPP
docker-compose restart backend
```

---

## 📊 Monitoring Commands

### Check System Health

```bash
# Health check
curl http://localhost:8000/health | jq

# System state
curl http://localhost:8000/api/control/state | jq

# Compliance status
curl http://localhost:8000/compliance/status | jq
```

### Monitor Logs

```bash
# Docker logs
docker-compose logs -f backend

# Or if running directly
tail -f logs/aitrapp.log
```

### Check Strategy Status

```bash
# List active strategies
curl http://localhost:8000/strategies | jq

# Strategy metrics
curl http://localhost:8000/metrics | grep strategy
```

### Monitor Positions

```bash
# Current positions
curl http://localhost:8000/positions | jq

# Portfolio status
curl http://localhost:8000/portfolio | jq
```

---

## 📈 What to Monitor

### During Market Hours (09:15-15:30 IST)

**Every 15 Minutes:**
- ✅ Signal generation per strategy
- ✅ Position entries and exits
- ✅ Portfolio heat (should stay < 1.5%)
- ✅ Daily P&L

**Hourly:**
- ✅ Win rate per strategy
- ✅ Risk-reward ratios
- ✅ Stop loss execution
- ✅ Error logs

**Key Times:**
- **09:15 AM:** Market opens - Monitor opening range strategies (ORB)
- **12:00 PM:** Mid-day review - Assess morning performance
- **15:15 PM:** Pre-close - Verify EOD square-off enabled
- **15:25 PM:** EOD square-off - All positions should close
- **15:30 PM:** Market closes

### After 24 Hours

**Review Metrics:**
1. **Signal Generation:**
   - Which strategies generated the most signals?
   - Which had the best signal quality?
   - Any strategies with no signals?

2. **Performance:**
   - Win rate per strategy (target: >50%)
   - Average R:R ratio (target: >1.5)
   - Maximum drawdown (target: <10%)
   - Total P&L

3. **Risk Management:**
   - Did stop losses trigger correctly?
   - Were position limits respected?
   - Portfolio heat stayed within limits?

4. **Issues:**
   - Any errors in logs?
   - Strategies that crashed or failed?
   - Market data issues?
   - Execution problems?

---

## 🎯 Success Criteria

### For Each Strategy:

✅ **Signal Generation:**
- Generated at least 1-2 signals during test period
- Signals were logical and well-timed
- No false signals or noise

✅ **Execution:**
- Orders placed correctly
- Stop losses and targets set properly
- Position sizing correct

✅ **Risk Management:**
- Stop losses triggered when needed
- Position limits respected
- Portfolio heat stayed within limits

✅ **Performance:**
- Win rate > 40% (minimum)
- R:R ratio > 1.2 (minimum)
- No major drawdowns

---

## 📝 Review Checklist (After 24 Hours)

- [ ] All 12 strategies loaded successfully
- [ ] No errors in startup logs
- [ ] Market data streaming correctly
- [ ] Strategies generating signals
- [ ] Orders executing (in paper mode)
- [ ] Stop losses working
- [ ] EOD square-off executed
- [ ] Performance metrics collected
- [ ] Logs reviewed for issues
- [ ] Ready for continued testing or adjustments

---

## 🔧 Troubleshooting

### Issue: Strategies Not Loading

```bash
# Check logs
docker-compose logs backend | grep -i error

# Verify config
grep -c "enabled: true" configs/app.yaml

# Check imports
python3 -c "from packages.core.strategies.macd_strategy import MACDStrategy"
```

### Issue: No Signals Generated

- Check market hours (09:15-15:30 IST)
- Verify market data is streaming
- Check strategy parameters
- Review logs for validation failures

### Issue: System Crashes

```bash
# Check system resources
docker stats

# Check logs
docker-compose logs backend --tail 100

# Restart
docker-compose restart backend
```

---

## 📊 Performance Tracking

### Metrics to Track:

1. **Per Strategy:**
   - Signals generated
   - Trades executed
   - Win rate
   - Average R:R
   - Max drawdown

2. **Overall:**
   - Total signals
   - Total trades
   - Portfolio P&L
   - Portfolio heat
   - Daily loss

### Export Data:

```bash
# Export trades (if endpoint exists)
curl http://localhost:8000/trades/export > trades_24h.csv

# Export metrics
curl http://localhost:8000/metrics > metrics_24h.txt
```

---

## 🎉 Next Steps After 24 Hours

1. **Review Performance:**
   - Identify best performing strategies
   - Identify underperforming strategies
   - Note any issues or bugs

2. **Adjustments:**
   - Fine-tune parameters for underperformers
   - Disable strategies with issues
   - Optimize position sizing

3. **Continue Testing:**
   - Extend paper testing to 1-2 weeks
   - Test across different market conditions
   - Validate risk management

4. **LIVE Deployment:**
   - Only after 2+ weeks of successful paper trading
   - Enable one strategy at a time
   - Monitor closely

---

## ✅ Current Status

**Mode:** PAPER ✅  
**Strategies Enabled:** 12/12 ✅  
**Risk Limits:** Conservative (0.35% per trade, 1.5% portfolio heat)  
**Status:** Ready for 24-hour paper trading test

**All systems ready! 🚀**

