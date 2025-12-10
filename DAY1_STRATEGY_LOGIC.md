# 🎯 DAY-1 STRATEGY LOGIC EXPLAINED

This document explains **exactly** what each strategy will do, when it will fire, and what positions you'll see.

---

## 🔷 STRATEGY 1: OptionsRanker (Debit Spreads)

### What It Does:
Buys directional option spreads (defined risk) based on opening range breakout + trend confirmation.

### Entry Logic:

```
IF time >= 09:30 AND time <= 14:00:
    IF NIFTY breaks above ORB high:
        IF EMA34 > EMA89 (uptrend confirmed):
            IF IV percentile between 20-80:
                IF liquidity score >= 70%:
                    → BUY CALL DEBIT SPREAD

    IF NIFTY breaks below ORB low:
        IF EMA34 < EMA89 (downtrend confirmed):
            IF IV percentile between 20-80:
                IF liquidity score >= 70%:
                    → BUY PUT DEBIT SPREAD
```

### Position Structure (CALL DEBIT SPREAD Example):

```
Leg 1: BUY  NIFTY 25-NOV 25350 CE @ ₹200  (ATM or slightly ITM)
Leg 2: SELL NIFTY 25-NOV 25400 CE @ ₹150  (OTM)

Net Debit Paid: ₹50 × 25 qty = ₹1,250
Max Loss: ₹1,250 (if NIFTY stays below 25350 at expiry)
Max Gain: (₹50 spread width - ₹50 debit) × 25 = ₹1,250 (if NIFTY above 25400)
Breakeven: 25350 + 50 = 25400
```

### Expected Behavior:

**If Bullish Signal (ORB breakout up + uptrend):**
```
09:32 - Signal generated: "NIFTY ORB breakout confirmed, EMA34 > EMA89"
09:33 - Orders placed:
  - BUY 25 NIFTY 25350 CE @ ₹200 (LIMIT)
  - SELL 25 NIFTY 25400 CE @ ₹150 (LIMIT)
09:34 - Both legs filled, position established
  - Net debit: ₹1,250
  - Risk: ₹625 (50% stop)
  - Target: ₹875 (70% gain)

During Trade:
  - Stop Loss: If spread value drops to ₹25 (50% loss) → Close position
  - Take Profit: If spread value rises to ₹85 (70% gain) → Close position
  - Time Stop: If still open after 20 minutes and no SL/TP → Close position

Exit:
  - Sell the long leg, Buy back the short leg
  - Realized PnL: Actual exit price - ₹50 entry debit
```

### What You'll See in Monitoring:

```json
{
  "position_id": "OptionsRanker_NIFTY_20251125_CALL_SPREAD",
  "strategy": "OptionsRanker",
  "instrument": "NIFTY 25350/25400 CE Spread",
  "quantity": 25,
  "entry_price": 50.0,
  "current_price": 62.0,
  "unrealized_pnl": 300.0,
  "pnl_pct": 24.0,
  "risk": 625.0,
  "stop_loss": 25.0,
  "take_profit": 85.0
}
```

### Scenarios:

**Scenario A: Quick Win (Common)**
- 09:35: Position entered at ₹50 debit
- 10:05: NIFTY rallies, spread value → ₹85
- 10:05: TP hit, position closed
- **Result: +₹875 profit (70% gain)**

**Scenario B: Stop Out (Common)**
- 09:35: Position entered at ₹50 debit
- 10:10: NIFTY reverses, spread value → ₹25
- 10:10: SL hit, position closed
- **Result: -₹625 loss (50% loss)**

**Scenario C: Time Stop (Less Common)**
- 09:35: Position entered at ₹50 debit
- 09:55: 20 minutes elapsed, spread at ₹48 (slight loss)
- 09:55: Time stop triggers, position closed
- **Result: -₹50 loss (4% loss)**

**Scenario D: No Signal (Possible)**
- ORB breakout happens but EMA34 < EMA89 (no trend confirmation)
- OR IV percentile outside 20-80 range
- OR liquidity score <70%
- **Result: No trade taken**

---

## 🔶 STRATEGY 2: expiry_short_strangle

### What It Does:
Sells out-of-the-money (OTM) options on both sides (call + put) to collect theta premium. Bets that NIFTY stays range-bound and options expire worthless.

### Entry Logic:

```
IF time >= 10:30 AND time <= 12:00:
    IF OptionsRanker has NOT taken a position (or already closed):
        IF days to expiry between 2-7:
            IF IV percentile between 40-85 (elevated IV):
                IF regime is LOW_MEAN_REVERT or MEDIUM_TREND (not HIGH_EVENT):
                    IF target delta ~0.20 options available:
                        IF expected premium ≥ ₹3,000 per lot:
                            → SELL SHORT STRANGLE
```

### Position Structure:

```
Leg 1: SELL NIFTY 25-NOV 25500 CE @ ₹180  (OTM call, delta ~0.20)
Leg 2: SELL NIFTY 25-NOV 25200 PE @ ₹170  (OTM put, delta ~0.20)

Premium Collected: (₹180 + ₹170) × 25 qty = ₹8,750
Max Loss: Unlimited (theoretically, limited by H1 tail hedge)
Max Gain: ₹8,750 (if both options expire worthless)
Breakeven: 25500 + 350 = 25850 (upside), 25200 - 350 = 24850 (downside)
```

### Expected Behavior:

**If Signal Fires:**
```
10:35 - Signal generated: "NIFTY short strangle opportunity, IVP=55, regime=LOW"
10:36 - Orders placed:
  - SELL 25 NIFTY 25500 CE @ ₹180 (LIMIT)
  - SELL 25 NIFTY 25200 PE @ ₹170 (LIMIT)
10:37 - Both legs filled, premium collected: ₹8,750
10:38 - H1 tail hedge triggered (see below)

During Trade:
  - Take Profit: If premium decays 50% (collect ₹4,375) → Close position
  - Stop Loss: If loss reaches 2x premium (₹17,500 loss) → Close position
  - Time Exit: Close 1 day before expiry

Exit:
  - Buy back both legs at current market price
  - Realized PnL: ₹8,750 collected - repurchase cost
```

### What You'll See in Monitoring:

```json
{
  "position_id": "expiry_short_strangle_NIFTY_20251125",
  "strategy": "expiry_short_strangle",
  "legs": [
    {
      "instrument": "NIFTY 25500 CE",
      "quantity": -25,
      "entry_price": 180.0,
      "current_price": 160.0,
      "unrealized_pnl": 500.0
    },
    {
      "instrument": "NIFTY 25200 PE",
      "quantity": -25,
      "entry_price": 170.0,
      "current_price": 155.0,
      "unrealized_pnl": 375.0
    }
  ],
  "premium_collected": 8750.0,
  "current_value": 7875.0,
  "unrealized_pnl": 875.0,
  "pnl_pct": 10.0,
  "max_loss": 17500.0
}
```

### Scenarios:

**Scenario A: Theta Win (Target)**
- 10:35: Short strangle entered, collect ₹8,750
- 12:00: NIFTY stays range-bound, premium decays
- 12:00: Premium decayed 50%, close at ₹4,375 cost
- **Result: +₹4,375 profit (50% of premium kept)**

**Scenario B: Stop Loss Hit (Risk)**
- 10:35: Short strangle entered, collect ₹8,750
- 13:00: NIFTY breaks out sharply, call value explodes
- 13:00: Loss reaches ₹17,500 (2x premium), stop hit
- **Result: -₹17,500 loss (but H1 tail hedge offsets some)**

**Scenario C: Expiry Approach (Common)**
- 10:35: Short strangle entered (3 days to expiry)
- 24-NOV: 1 day before expiry, premium at ₹3,000
- 24-NOV: Time exit triggered, close position
- **Result: +₹5,750 profit (₹8,750 - ₹3,000)**

**Scenario D: No Signal (Possible)**
- IV percentile too low (IVP <40)
- OR regime is HIGH_EVENT or CHAOTIC
- OR OptionsRanker position still open
- **Result: No trade taken**

---

## 🛡️ STRATEGY 3: TailShortVolOverlay (H1)

### What It Does:
**Automatic tail hedge** that deploys when short premium strategies (like expiry_short_strangle) fire. Buys deep OTM puts to protect against tail risk (market crash).

### Entry Logic:

```
IF expiry_short_strangle position is opened:
    Calculate short_premium_notional = ₹8,750 (example)
    Target_tail_notional = 15% of short_premium = ₹1,312

    Find deep OTM put (5% below spot):
        Buy NIFTY 24800 PE @ ₹50
        Quantity = ₹1,312 / ₹50 / 25 = ~1 lot

    → BUY 25 NIFTY 24800 PE (tail hedge)
```

### Position Structure:

```
Underlying: expiry_short_strangle (₹8,750 premium collected)
Tail Hedge: BUY 25 NIFTY 24800 PE @ ₹50

Tail Cost: ₹50 × 25 = ₹1,250 (14% of short premium)
Tail Max Gain: Unlimited (if NIFTY crashes)
Net Premium After Tail: ₹8,750 - ₹1,250 = ₹7,500
```

### Expected Behavior:

**Normal Scenario (No Crash):**
```
10:38 - Short strangle opened, collected ₹8,750
10:39 - H1 tail hedge deployed: BUY 24800 PE @ ₹50 (cost ₹1,250)
12:00 - NIFTY stays range-bound
  - Short strangle: +₹4,375 (50% decay)
  - Tail hedge: -₹1,250 (expires worthless)
  - Net PnL: +₹3,125
```

**Crash Scenario (Tail Hedge Saves You):**
```
10:38 - Short strangle opened, collected ₹8,750
10:39 - H1 tail hedge deployed: BUY 24800 PE @ ₹50
11:30 - NIFTY crashes 500 points (black swan event)
  - Short strangle: -₹30,000 (short puts go ITM)
  - Tail hedge: +₹25,000 (deep OTM put now valuable)
  - Net Loss: -₹5,000 (instead of -₹30,000)
  - Tail hedge LIMITED the damage
```

### What You'll See in Monitoring:

```json
{
  "position_id": "H1_tail_NIFTY_24800PE",
  "strategy": "TailShortVolOverlay",
  "instrument": "NIFTY 24800 PE",
  "quantity": 25,
  "entry_price": 50.0,
  "current_price": 45.0,
  "unrealized_pnl": -125.0,
  "note": "Tail hedge for expiry_short_strangle",
  "linked_position": "expiry_short_strangle_NIFTY_20251125"
}
```

### Coverage Calculation:

```
Short Premium Collected: ₹8,750
Tail Hedge Cost: ₹1,250
Coverage %: (₹1,250 / ₹8,750) × 100 = 14.3%

Target: 15% coverage (H1 config)
Minimum: 10% coverage (below this = dangerous)
Maximum: 25% coverage (above this = over-hedged)

Current: 14.3% → WITHIN BOUNDS ✓
```

### Scenarios:

**Scenario A: Normal Market (Most Common)**
- Tail hedge decays to ₹20
- Loss on tail: -₹750
- Gain on short strangle: +₹4,375
- **Net: +₹3,625 (tail hedge was insurance cost)**

**Scenario B: Moderate Move (Common)**
- NIFTY moves 2%, tail hedge stays near ₹50
- Loss on tail: -₹0
- Gain on short strangle: +₹3,000
- **Net: +₹3,000**

**Scenario C: Crash (Rare but Important)**
- NIFTY crashes 5%, tail hedge → ₹500
- Gain on tail: +₹11,250
- Loss on short strangle: -₹17,500
- **Net: -₹6,250 (instead of -₹17,500 without tail)**

**Scenario D: No Deployment**
- expiry_short_strangle didn't fire
- **No tail hedge deployed**

---

## 📊 COMBINED STRATEGY SCENARIOS

### Scenario 1: Both Strategies Fire (Rare on Day-1)

```
09:35 - OptionsRanker: Call debit spread entered (₹1,250 debit)
10:00 - OptionsRanker: TP hit, +₹875 profit, closed

10:35 - expiry_short_strangle: Short strangle entered (₹8,750 premium)
10:36 - H1: Tail hedge deployed (₹1,250 cost)

End of Day:
  - OptionsRanker: +₹875 (closed)
  - expiry_short_strangle: +₹4,375 (50% decay)
  - H1 tail: -₹750 (decayed)

Total PnL: +₹4,500
```

### Scenario 2: Only OptionsRanker Fires (More Likely on Day-1)

```
09:35 - OptionsRanker: Put debit spread entered
10:15 - OptionsRanker: SL hit, -₹625 loss, closed

10:35 onwards:
  - expiry_short_strangle: No signal (IV too low)
  - H1: No deployment (no short premium)

Total PnL: -₹625
```

### Scenario 3: Only Short Strangle Fires

```
Morning:
  - OptionsRanker: No signal (no ORB breakout)

10:35 - expiry_short_strangle: Short strangle entered
10:36 - H1: Tail hedge deployed

13:00:
  - Short strangle: +₹3,000 (partial decay)
  - H1 tail: -₹500 (decay)

Total PnL: +₹2,500
```

### Scenario 4: No Signals All Day (Possible)

```
09:30-14:00:
  - OptionsRanker: No ORB breakout or no trend confirmation
  - expiry_short_strangle: IV too low or regime blocked

Total PnL: ₹0 (no trades)
```

---

## 🎯 DECISION TREE (What Will Happen When)

```
09:15 - Market Opens
  ↓
09:15-09:30 - ORB Window (bot collecting data, NO TRADES)
  ↓
09:30 - Entry Window Opens
  ↓
OptionsRanker Evaluation:
  ├─ ORB breakout + trend + IV + liquidity → YES → Enter Debit Spread
  └─ Any condition fails → NO → Wait
      ↓
10:30 - Short Premium Window Opens
  ↓
Check: OptionsRanker Position Open?
  ├─ YES → Block expiry_short_strangle (only 1 primary position today)
  └─ NO → Evaluate expiry_short_strangle
      ↓
      Check: IV elevated + regime OK + premium ≥ ₹3K?
        ├─ YES → Enter Short Strangle
        │    ↓
        │    H1 Auto-Deploy: Buy Tail Hedge (15% of premium)
        └─ NO → Wait or no more trades today
            ↓
14:00 - Entry Window Closes (no new positions)
  ↓
15:20 - EOD Squareoff (all positions auto-closed)
```

---

## 📋 WHAT TO EXPECT (REALISTIC OUTCOMES)

### Most Likely Outcome:
- 0-1 trade (OptionsRanker fires OR short strangle fires, not both)
- PnL: -₹2,000 to +₹4,000
- All exits work correctly
- No orphan positions
- **Learning: Infrastructure works**

### Best Case Outcome:
- 2 trades (both fire, both win)
- PnL: +₹4,000 to +₹6,000
- **Learning: Strategies profitable**

### Worst Case Outcome:
- 2 trades (both fire, both lose)
- PnL: -₹6,000 to -₹8,000
- **Still within daily loss limit (-₹25K)**
- **Learning: Strategies need tuning, but risk management worked**

### Nothing Happens Outcome:
- 0 trades (no signals all day)
- PnL: ₹0
- **Learning: Signal generation logic is conservative (maybe too conservative?)**

---

## ✅ SUCCESS = INFRASTRUCTURE VALIDATION, NOT PnL

**You're testing:**
- ✅ Do orders get placed correctly?
- ✅ Do positions appear in bot and broker?
- ✅ Do exits trigger at the right levels?
- ✅ Do tail hedges auto-deploy?
- ✅ Does EOD flatten work?

**You're NOT testing:**
- ❌ Long-term profitability (need 50+ trades)
- ❌ Strategy optimization
- ❌ Parameter tuning

**Goal:** Walk before you run. Prove the car starts and the brakes work. Speed comes later.

---

**🚀 You're ready. Good luck!**
