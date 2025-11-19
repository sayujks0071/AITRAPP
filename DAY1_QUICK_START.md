# ⚡ DAY-1 LIVE QUICK START

**5-Minute Setup Guide for First Live Trading Session**

---

## ✅ PRE-FLIGHT CHECKLIST

### 1. Manual Kite Verification (08:30 IST)
```
[ ] Login to kite.zerodha.com
[ ] Verify 0 open positions
[ ] Verify 0 pending orders
[ ] Verify margin ≈ ₹10,00,000
[ ] Get fresh access token for today
```

### 2. Start Bot (08:55 IST)
```bash
# Set environment
export APP_MODE=LIVE
export APP_TIMEZONE=Asia/Kolkata
export KITE_API_KEY="your_key"
export KITE_ACCESS_TOKEN="fresh_token_from_today"

# Start with Day-1 config
python -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8000

# Verify startup
curl -s http://localhost:8000/health | jq .
# Should show: "mode": "LIVE", "status": "healthy"
```

### 3. Wait for Market Open (09:15 IST)
```bash
# At 09:17 (2 min after open), check ready status
curl -s http://localhost:8000/ready | jq .

# Must see:
# {
#   "ready": true,
#   "marketdata_heartbeat": 0.5,  // <5 = good
#   "leader": 1
# }

# If ready=false, DO NOT TRADE until this resolves
```

---

## 📊 MONITORING (09:30-15:30 IST)

### Every 15-30 Minutes:
```bash
bash scripts/day1_monitor.sh
```

**Watch for:**
- ✅ Ready status stays `true`
- ✅ Daily PnL stays above -₹25,000
- ✅ Margin usage stays below 30%
- ✅ Max 2 positions at any time

---

## 🚨 EMERGENCY CONTROLS

### Pause New Entries (keeps positions open)
```bash
curl -X POST http://localhost:8000/pause
```

### Flatten Everything Immediately
```bash
curl -X POST http://localhost:8000/flatten
```

### Resume Trading
```bash
curl -X POST http://localhost:8000/resume
```

---

## 📝 WHAT TO EXPECT TODAY

### Strategies Active:
1. **OptionsRanker (09:30-14:00)** - Debit spreads on NIFTY
   - Max 1 position
   - Risk per trade: ~₹1,000-₹2,000

2. **expiry_short_strangle (10:30-12:00)** - Short premium + tail hedge
   - Only if OptionsRanker didn't fire
   - Risk per trade: ~₹17,500 (hedged by H1 tail)

### Expected Outcomes:
- **Trades:** 0-2 (likely 0-1)
- **PnL Range:** -₹8,000 to +₹6,000
- **Goal:** Prove infrastructure works (not to make money)

---

## 📋 END-OF-DAY (15:25 IST)

### Verify Auto-Flatten:
```bash
# Check all positions closed
curl -s http://localhost:8000/positions | jq '.count'
# Should return: 0

# Check final PnL
curl -s http://localhost:8000/risk | jq '{daily_pnl, realized_pnl_today}'
```

### Manual Verification:
```
[ ] Bot shows 0 positions
[ ] Kite shows 0 positions
[ ] No pending orders
[ ] Logs saved
```

---

## 📚 DETAILED DOCS

- **Full Runbook:** [DAY1_LIVE_RUNBOOK.md](DAY1_LIVE_RUNBOOK.md)
- **Strategy Logic:** [DAY1_STRATEGY_LOGIC.md](DAY1_STRATEGY_LOGIC.md)
- **Config File:** [configs/kite_day1_live.yaml](configs/kite_day1_live.yaml)

---

## 🎯 SUCCESS CRITERIA

### Must Achieve:
- ✅ No execution errors
- ✅ No position size errors
- ✅ No orphan positions
- ✅ Risk limits respected
- ✅ EOD flatten worked

### Don't Care About:
- ❌ Total PnL (can be negative)
- ❌ Win rate (too few trades)
- ❌ Beating market

**Goal:** Prove the plumbing works. That's it.

---

## ⚠️ WHEN TO STOP TRADING

**Immediate Flatten If:**
- Ready status goes `false` during market hours
- Orphan position detected (position in Kite not in bot)
- Position size 10x larger than expected
- PnL moving much faster than expected
- Short strangle fires but NO tail hedge

**Pause New Entries If:**
- Daily loss reaches -₹15,000
- Margin usage exceeds 25%
- 2 consecutive losing trades

**Hard Stop (No Override):**
- Daily loss reaches -₹25,000
- System not leader
- Market data heartbeat >10 seconds

---

## 🚀 YOU'RE READY

1. ✅ Config created: [kite_day1_live.yaml](configs/kite_day1_live.yaml)
2. ✅ Monitor script ready: `bash scripts/day1_monitor.sh`
3. ✅ Strategies configured: OptionsRanker + expiry_short_strangle + H1
4. ✅ Caps set: Max 2 positions, max ₹8K risk
5. ✅ Safety gates: Auto-stop at -₹25K, 30% margin

**All that's left:** Manual Kite verification → Start bot → Wait for 09:15 → Let it run.

**Good luck on your first live session!** 🎯
