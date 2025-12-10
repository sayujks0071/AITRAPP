# 📘 DAY-1 LIVE TRADING RUNBOOK

**Date:** Use this for your first live trading session
**Capital:** ₹1,000,000
**Max Risk:** ₹8,000 (0.8%)
**Strategies:** OptionsRanker (debit spreads) + expiry_short_strangle + H1 tails

---

## ⏰ PRE-MARKET CHECKLIST (08:30-09:15 IST)

### 1. Manual Kite Verification
Login to https://kite.zerodha.com and verify:

```
[ ] Positions: 0 open positions
[ ] Orders: 0 pending/AMO orders
[ ] Funds: Available margin ≈ ₹10,00,000
[ ] Holdings: No unexpected holdings
```

### 2. Start Bot with Day-1 Config

```bash
# Set environment
export APP_MODE=LIVE
export APP_TIMEZONE=Asia/Kolkata
export KITE_API_KEY="your_api_key"
export KITE_ACCESS_TOKEN="fresh_token_from_today"

# Start with Day-1 config
python -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8000
```

### 3. Verify System Health (08:55 IST)

```bash
# Check health
curl -s http://localhost:8000/health | jq .

# Should see:
# {
#   "status": "healthy",
#   "mode": "LIVE",
#   "is_paused": false
# }
```

```bash
# Check risk state
curl -s http://localhost:8000/risk | jq .

# Should see:
# {
#   "used_margin": 0,
#   "available_margin": 1000000,
#   "open_positions_count": 0,
#   "can_take_new_position": true
# }
```

---

## 🚦 MARKET OPEN (09:15 IST)

### 4. Verify Market Data is Flowing

**CRITICAL:** Wait 2-3 minutes after 09:15 for data to stabilize.

```bash
curl -s http://localhost:8000/ready | jq .
```

**Must see:**
```json
{
  "ready": true,
  "marketdata_heartbeat": 0.5,  // <5 seconds = good
  "order_stream_heartbeat": 0.2,
  "scan_heartbeat": 0.3,
  "leader": 1
}
```

**If `ready: false`:** DO NOT TRADE. Debug marketdata connection first.

### 5. ORB Window (09:15-09:30)

**Do nothing.** Let the 15-minute opening range form.

The bot will:
- Collect first 15-minute candle data
- Calculate ORB high/low
- Prepare for breakout signals at 09:30

---

## 📊 TRADING WINDOW (09:30-14:00 IST)

### Strategy Sequencing

#### **Phase 1: OptionsRanker (09:30-10:30)**

**What to expect:**
- Bot looks for ORB breakout + trend confirmation
- If signal fires: Places 1 debit spread (2 legs, defined risk)
- Entry: Buy closer strike, sell further strike (call or put spread)

**Monitor:**
```bash
# Check positions every 5 minutes
curl -s http://localhost:8000/positions | jq .
```

**Expected if signal fires:**
```json
{
  "positions": [
    {
      "position_id": "OptionsRanker_NIFTY_...",
      "strategy": "OptionsRanker",
      "instrument": "NIFTY25350CE (example)",
      "side": "LONG_SPREAD",
      "quantity": 25,
      "entry_price": 3200.0,
      "current_price": 3250.0,
      "unrealized_pnl": 1250.0,
      "risk": 2000.0  // Net debit paid
    }
  ]
}
```

**If position taken:**
- ✅ Max loss: ~₹2,000 (50% of debit)
- ✅ Max gain: ~₹1,400-₹2,800 (70% of debit)
- ✅ Exits: Auto-triggered at -50% or +70%

**If NO signal by 10:30:** Normal. Move to Phase 2.

---

#### **Phase 2: Short Premium (10:30-12:00)**

**Triggers IF:**
- OptionsRanker didn't fire
- OR OptionsRanker position already closed
- Current time ≥ 10:30 IST

**What to expect:**
- Bot evaluates NIFTY short strangle opportunity
- Checks: IV elevated (IVP >40), regime not HIGH_EVENT
- If signal fires: Sells 1 strangle (2 short legs: OTM call + OTM put)

**Monitor:**
```bash
curl -s http://localhost:8000/positions | jq .
```

**Expected if signal fires:**
```json
{
  "positions": [
    {
      "position_id": "expiry_short_strangle_NIFTY_...",
      "strategy": "expiry_short_strangle",
      "legs": [
        {
          "instrument": "NIFTY25400CE",
          "quantity": -25,  // SHORT
          "entry_price": 180.0
        },
        {
          "instrument": "NIFTY25300PE",
          "quantity": -25,  // SHORT
          "entry_price": 170.0
        }
      ],
      "premium_collected": 8750.0,  // (180+170) × 25
      "unrealized_pnl": 500.0,
      "max_loss": 17500.0  // 2x premium
    }
  ]
}
```

**If short strangle fires, H1 tail hedge should auto-deploy:**

```bash
# Check for tail hedge position
curl -s http://localhost:8000/positions | jq '.positions[] | select(.strategy=="TailShortVolOverlay")'
```

**Expected tail hedge:**
```json
{
  "position_id": "H1_tail_NIFTY_...",
  "strategy": "TailShortVolOverlay",
  "instrument": "NIFTY24800PE (deep OTM)",
  "quantity": 25,  // LONG
  "entry_price": 50.0,  // Small premium paid
  "risk": 1250.0,  // ~15% of short premium collected
  "note": "Tail hedge for short strangle"
}
```

**If NO tail hedge appears within 5 minutes of short strangle:**
```bash
# MANUALLY FLATTEN - something is wrong
curl -X POST http://localhost:8000/flatten
```

---

## 🔍 INTRADAY MONITORING (Every 15-30 min)

### Quick Health Check Script

```bash
#!/bin/bash
# save as: scripts/day1_quick_check.sh

echo "=== DAY-1 LIVE HEALTH CHECK ==="
echo ""

echo "1. System State:"
curl -s http://localhost:8000/state | jq '{mode, is_paused, positions_count, daily_pnl}'
echo ""

echo "2. Risk State:"
curl -s http://localhost:8000/risk | jq '{used_margin, margin_pct: (.used_margin / 1000000 * 100), daily_pnl, daily_loss_limit, can_take_new_position}'
echo ""

echo "3. Positions:"
curl -s http://localhost:8000/positions | jq '.positions[] | {strategy, instrument, unrealized_pnl}'
echo ""

echo "4. Ready Status:"
curl -s http://localhost:8000/ready | jq '{ready, leader, marketdata_heartbeat, scan_heartbeat}'
echo ""
```

Run every 15-30 minutes:
```bash
bash scripts/day1_quick_check.sh
```

---

## 🚨 RISK LIMITS & CIRCUIT BREAKERS

### Automatic Stops (Bot enforces these)

| Limit | Value | Action |
|-------|-------|--------|
| Max Positions | 2 | Block new entries |
| Daily Loss | -₹25,000 | Auto-pause new entries |
| Margin Used | 30% (₹300K) | Block new entries |
| Per-Trade Risk | ₹3,000 | Reject oversized signals |

### Manual Intervention Thresholds

**YELLOW (Watch closely):**
- Daily PnL < -₹12,500
- Margin used >20%
- Any position down >30%

**RED (Consider manual flatten):**
- Daily PnL < -₹20,000
- Margin used >25%
- Any position down >50%
- Unexpected position appeared (orphan)

### Emergency Flatten

```bash
# Pause new entries (keeps positions open)
curl -X POST http://localhost:8000/pause

# Flatten everything immediately
curl -X POST http://localhost:8000/flatten

# Resume trading (only if safe)
curl -X POST http://localhost:8000/resume
```

---

## 🕐 END-OF-DAY (15:00-15:30 IST)

### Automatic EOD Squareoff

Bot should auto-flatten all positions at **15:20 IST** (per config).

### Manual Verification (15:25 IST)

```bash
# Verify all positions closed
curl -s http://localhost:8000/positions | jq '.count'
# Should return: 0

# Check final PnL
curl -s http://localhost:8000/risk | jq '{daily_pnl, realized_pnl_today}'
```

### Post-Market Checklist

```
[ ] All positions closed (bot shows 0)
[ ] Kite shows 0 positions
[ ] Orders all completed (none pending)
[ ] Daily PnL recorded
[ ] No orphan positions
[ ] Logs saved for review
```

---

## 📈 SUCCESS METRICS (DAY-1)

### Primary Goals (Must achieve):
- ✅ No execution errors (all orders placed correctly)
- ✅ No position size errors (lot sizes correct)
- ✅ No orphan positions (bot-broker sync)
- ✅ Risk limits respected (no breaches)
- ✅ EOD flatten worked (all closed by 15:25)

### Secondary Goals (Nice to have):
- Positive PnL (but don't stress if negative)
- At least 1 signal fired (validates strategy logic)
- Exits triggered correctly (SL/TP worked)

### Don't Care About:
- Total PnL amount (1-2 trades = not statistically meaningful)
- Win rate (need 20+ trades for meaningful data)
- Beating benchmarks

**Goal:** Prove the infrastructure works. That's the only thing that matters today.

---

## 🐛 TROUBLESHOOTING

### Issue: `/ready` stays `false` after 09:20

**Diagnosis:**
```bash
curl -s http://localhost:8000/ready | jq .
```

If `marketdata_heartbeat` is still >5 seconds:
1. Check Kite access token is valid
2. Check network connectivity
3. Check logs for websocket errors
4. **DO NOT TRADE** until this resolves

### Issue: Short strangle fired but NO tail hedge

**Immediate action:**
```bash
# Flatten the short strangle
curl -X POST http://localhost:8000/flatten
```

**Why:** Short premium without tail hedge = unlimited risk

### Issue: Position shows in Kite but not in bot

**Orphan position detected.**

**Immediate action:**
```bash
# Pause bot
curl -X POST http://localhost:8000/pause

# Manually close orphan in Kite

# After confirmed closed, resume bot
curl -X POST http://localhost:8000/resume
```

### Issue: PnL moving way faster than expected

**Possible causes:**
- Wrong lot size (e.g. 50 lots instead of 1)
- Wrong instrument (traded wrong expiry)
- Slippage on illiquid option

**Immediate action:**
```bash
# Check position details
curl -s http://localhost:8000/positions | jq '.positions[] | {instrument, quantity, entry_price, current_price, unrealized_pnl}'

# If quantity is wrong (e.g. 1250 instead of 25):
# FLATTEN IMMEDIATELY
curl -X POST http://localhost:8000/flatten
```

---

## 📞 FINAL CHECKLIST

### Before First Trade:
```
[ ] Kite manually verified (0 positions, 0 orders)
[ ] Bot showing ready: true
[ ] Marketdata heartbeat <5 seconds
[ ] Leader status = 1
[ ] No positions in bot
[ ] Current time between 09:30-14:00
```

### After First Trade:
```
[ ] Position appeared in bot within 10 seconds
[ ] Position matches what you expected (instrument, quantity)
[ ] Risk amount is correct (~₹2,000-₹4,000)
[ ] If short premium: tail hedge deployed
```

### End of Day:
```
[ ] All positions auto-closed by 15:25
[ ] Bot shows 0 positions
[ ] Kite shows 0 positions
[ ] No pending orders
[ ] Daily PnL recorded
```

---

**🎯 Remember:** You're not trying to make money today. You're trying to prove the system works. Treat it like a production deployment test, not a trading competition.

**Good luck on your first live session!** 🚀
