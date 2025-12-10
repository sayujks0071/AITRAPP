# 🎯 Day-4 Premium Strategies Configuration Summary

**Date:** 2025-11-19  
**Status:** ✅ CONFIGURATION COMPLETE  
**Capital:** ₹1,000,000  
**Mode:** LIVE (NSE/Kite)

---

## 📊 Executive Summary

Successfully enabled **G1 (GammaScalper)**, **T1 (CalendarArb)**, and **D1 (DispersionArb)** for Day-4 LIVE trading with **tiny, controlled risk limits**. All strategies are now active alongside **OptionsRanker** (primary) and **expiry_short_strangle** (secondary).

### Key Changes

1. ✅ **R1 (RegimeVolEngine)**: Enabled as meta-strategy (priority 0)
2. ✅ **G1 (GammaScalper)**: Promoted to LIVE with tiny size (1 lot, ₹5k daily loss cap)
3. ✅ **T1 (CalendarArb)**: Promoted to LIVE with tiny size (1 lot, ₹5k daily loss cap)
4. ✅ **D1 (DispersionArb)**: Promoted to LIVE with tiny size (1 lot, ₹5k daily loss cap)
5. ✅ **H1 (TailShortVolOverlay)**: Confirmed as overlay-only (auto-hedges short vol)

---

## 🎯 Strategy Configuration Details

### Primary Strategy (Unchanged)

**OptionsRanker** (Debit Spreads)
- **Status:** ✅ LIVE (unchanged)
- **Max Positions:** 1
- **Max Lot Size:** 1
- **Capital Allocation:** 45% (via allocator)
- **Daily Loss Cap:** Global limit applies (-₹25,000)

### Premium Strategies (Newly Enabled)

#### **G1: GammaScalper** (Long Gamma with Futures Hedge)

**Config File:** `configs/gamma_scalper.yaml`

**Risk Limits (Day-4):**
- `max_positions`: **1** per underlying
- `lots_per_underlying`: **1**
- `max_capital_pct`: **10%** (₹100,000 max)
- `max_daily_loss_absolute`: **₹5,000** (hard cap)
- `max_daily_loss_pct`: **0.5%** of capital

**Entry Window:**
- Start: **09:45** IST (conservative)
- End: **15:15** IST

**Capital Allocation:** **15%** (via allocator)

**Regime Requirements:**
- Requires R1 regime classification
- Allowed regimes: `MEDIUM_TREND`, `HIGH_EVENT`

---

#### **T1: CalendarArb** (Term Structure Arbitrage)

**Config File:** `configs/calendar_arb.yaml`

**Risk Limits (Day-4):**
- `max_positions`: **1** per underlying
- `max_lots_per_underlying`: **1** (reduced from 3)
- `max_open_calendars_per_underlying`: **1** (reduced from 2)
- `max_capital_pct`: **10%** (₹100,000 max)
- `max_daily_loss_absolute`: **₹5,000** (hard cap)
- `max_daily_loss_pct`: **0.5%** of capital

**Entry Window:**
- Start: **10:00** IST (conservative)
- End: **14:30** IST

**Capital Allocation:** **15%** (via allocator)

**Regime Requirements:**
- Requires R1 regime classification
- Allowed regimes: `LOW_MEAN_REVERT`, `MEDIUM_TREND`, `HIGH_EVENT`

---

#### **D1: DispersionArb** (Sector vs Index Volatility)

**Config File:** `configs/dispersion_arb.yaml`

**Risk Limits (Day-4):**
- `max_positions`: **1** dispersion pair
- `max_pair_books_per_pair`: **1**
- `lots_sector_long_vol`: **1**
- `lots_parent_short_vol`: **1**
- `max_capital_pct`: **10%** (₹100,000 max)
- `max_daily_loss_absolute`: **₹5,000** (hard cap)
- `max_daily_loss_pct`: **0.5%** of capital

**Entry Window:**
- Start: **10:30** IST (midday only)
- End: **14:00** IST

**Capital Allocation:** **10%** (via allocator)

**Regime Requirements:**
- Requires R1 regime classification
- Allowed regimes: `LOW_MEAN_REVERT`, `MEDIUM_TREND`

---

### Overlay Strategy (Unchanged)

**H1: TailShortVolOverlay** (Auto-hedge for Short Premium)

**Config File:** `configs/tail_short_vol.yaml`

**Status:** ✅ **Overlay-only** (does not trade independently)

**Behavior:**
- Monitors short vol strategies: `expiry_short_strangle`, `intraday_short_strangle`, `vscore_credit_spread`, `drifting_credit_spread`, `calendar_arb`, `dispersion_arb`
- Automatically deploys deep OTM puts when short premium exposure exists
- Target coverage: **15%** of short premium notional
- Coverage range: **10-25%** (min-max)

**Capital Allocation:** Not applicable (overlay, not standalone)

---

## 📈 Strategy Allocator Configuration

**Config File:** `configs/strategy_allocator.yaml`

### Base Weights (Day-4)

| Strategy | Base Weight | Role | Status |
|----------|------------|------|--------|
| **OptionsRanker** | **45%** | directional_debit | ✅ LIVE |
| **expiry_short_strangle** | **10%** | income_short_vol | ✅ LIVE |
| **gamma_scalper (G1)** | **15%** | long_gamma | ✅ LIVE |
| **calendar_arb (T1)** | **15%** | term_structure | ✅ LIVE |
| **dispersion_arb (D1)** | **10%** | dispersion | ✅ LIVE |
| intraday_short_strangle | 0% | intraday_short_vol | ⚠️ Shadow |
| index_sniper | 0% | directional_trend | ⚠️ Shadow |
| drifting_credit_spread | 0% | directional_income | ⚠️ Shadow |
| vscore_credit_spread | 0% | vol_surface | ⚠️ Shadow |
| kurtosis_straddle | 0% | long_vol | ⚠️ Shadow |

**Total Active Weight:** **95%** (45% + 10% + 15% + 15% + 10%)

### Global Allocator Limits

- `global_max_capital_pct`: **60%** (unchanged)
- `max_capital_pct_per_strategy`: **25%** (unchanged)
- `min_capital_pct_per_strategy`: **1%** (unchanged)

---

## 🛡️ Global Risk Guardrails (Unchanged)

**Config File:** `configs/kite_day1_live.yaml`

### Daily Loss Limits
- **Hard Stop:** **-₹25,000** (-2.5% of capital) ✅ **UNCHANGED**
- **Soft Warning:** **~-₹12,500** (-1.25% of capital) ✅ **UNCHANGED**

### Position Limits
- **Max Total Positions:** **4** (up from 2 for Day-4)
  - OptionsRanker: 1
  - G1: 1
  - T1: 1
  - D1: 1
- **Max Capital Deployed:** **15%** (up from 8% for Day-4)
- **Max Margin Usage:** **30%** ✅ **UNCHANGED**

### Per-Strategy Daily Loss Caps (New)

| Strategy | Daily Loss Cap |
|----------|---------------|
| G1 (GammaScalper) | **₹5,000** |
| T1 (CalendarArb) | **₹5,000** |
| D1 (DispersionArb) | **₹5,000** |

**Note:** These are **in addition to** the global daily loss limit of -₹25,000.

---

## ✅ Configuration Validation

### YAML Syntax Validation
- ✅ `configs/kite_day1_live.yaml` - Valid
- ✅ `configs/gamma_scalper.yaml` - Valid
- ✅ `configs/calendar_arb.yaml` - Valid
- ✅ `configs/dispersion_arb.yaml` - Valid
- ✅ `configs/strategy_allocator.yaml` - Valid
- ✅ `configs/tail_short_vol.yaml` - Valid

### Strategy Loading Verification

**Enabled Strategies in Main Config:**
1. ✅ OptionsRanker (priority 1)
2. ✅ expiry_short_strangle (priority 2)
3. ✅ RegimeVolEngine (priority 0) - **NEW**
4. ✅ GammaScalper (priority 4) - **NEW**
5. ✅ CalendarArb (priority 5) - **NEW**
6. ✅ DispersionArb (priority 6) - **NEW**
7. ✅ TailShortVolOverlay (priority 3)

**Removed from Shadow Mode:**
- ✅ gamma_scalper (now LIVE)
- ✅ calendar_arb (now LIVE)
- ✅ dispersion_arb (now LIVE)

---

## 📋 Files Modified

1. **`configs/kite_day1_live.yaml`**
   - Added R1, G1, T1, D1 to `strategies` list (enabled)
   - Removed G1, T1, D1 from `shadow_strategies`
   - Updated `max_total_positions`: 2 → 4
   - Updated `max_capital_deployed_pct`: 8% → 15%

2. **`configs/gamma_scalper.yaml`**
   - Updated `entry_window`: 09:20-11:00 → 09:45-15:15
   - Added `max_positions`: 1
   - Updated `max_capital_pct`: 5% → 10%
   - Added `max_daily_loss_absolute`: 5000
   - Updated `max_daily_loss_pct`: 0.7% → 0.5%

3. **`configs/calendar_arb.yaml`**
   - Updated `entry_window`: 09:30-13:30 → 10:00-14:30
   - Updated `max_lots_per_underlying`: 3 → 1
   - Added `max_positions`: 1
   - Updated `max_capital_pct`: 5% → 10%
   - Added `max_daily_loss_absolute`: 5000
   - Updated `max_daily_loss_pct`: 0.7% → 0.5%
   - Updated `max_open_calendars_per_underlying`: 2 → 1

4. **`configs/dispersion_arb.yaml`**
   - Updated `entry_window`: 10:00-14:00 → 10:30-14:00
   - Added `max_positions`: 1
   - Updated `max_capital_pct`: 5% → 10%
   - Added `max_daily_loss_absolute`: 5000
   - Updated `max_daily_loss_pct`: 0.8% → 0.5%

5. **`configs/strategy_allocator.yaml`**
   - Added `OptionsRanker` with base_weight: 0.45
   - Updated `gamma_scalper` base_weight: 0.10 → 0.15
   - Updated `calendar_arb` base_weight: 0.10 → 0.15
   - Updated `dispersion_arb` base_weight: 0.05 → 0.10
   - Updated `expiry_short_strangle` base_weight: 0.20 → 0.10
   - Set shadow strategies to base_weight: 0.0

---

## 🚀 Day-4 Startup Checklist

### Pre-Market (Before 09:15 IST)

- [ ] Verify `.env` has `APP_MODE=LIVE`
- [ ] Verify `.env` has `APP_CONFIG=configs/kite_day1_live.yaml` (or ensure default loads it)
- [ ] Verify Kite token is fresh and valid
- [ ] Manually verify Kite account is flat (0 positions, 0 orders)

### Startup Commands

```bash
# Start API with LIVE mode
export APP_MODE=LIVE
export APP_CONFIG=configs/kite_day1_live.yaml  # Explicit (recommended)
python -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8000
```

### Post-Startup Verification (08:55-09:15 IST)

```bash
# Check system health
curl -s http://localhost:8000/health | jq .

# Check loaded strategies
curl -s http://localhost:8000/api/strategies/summary | jq '.strategies[] | {name: .name, enabled: .enabled}'

# Verify R1 regime classification
curl -s http://localhost:8000/metrics | grep algo_vol_regime_code

# Verify G1, T1, D1 are loaded
curl -s http://localhost:8000/state | jq '.strategies[] | select(.name | contains("Gamma") or contains("Calendar") or contains("Dispersion"))'
```

### Expected Behavior

1. **R1 (RegimeVolEngine)** should classify market regime immediately
2. **G1, T1, D1** should appear in `/state` endpoint as enabled strategies
3. **Allocator** should show correct weights for all strategies
4. **H1** should be loaded but inactive until short vol exposure exists

---

## 📊 Monitoring Day-4

### Key Metrics to Watch

1. **Regime Classification (R1)**
   - Check `/metrics` for `algo_vol_regime_code{underlying="NIFTY"}`
   - Should show: `LOW_MEAN_REVERT`, `MEDIUM_TREND`, `HIGH_EVENT`, or `CHAOTIC`

2. **G1 (GammaScalper)**
   - `gamma_scalper_books_opened{underlying="NIFTY"}`
   - `gamma_scalper_abs_delta{underlying="NIFTY"}` (should stay < 0.15)
   - `gamma_scalper_rebalances{underlying="NIFTY"}`

3. **T1 (CalendarArb)**
   - Calendar spreads opened/closed
   - Term structure signals

4. **D1 (DispersionArb)**
   - Dispersion pairs opened
   - Correlation and vol ratio metrics

5. **Daily Loss Tracking**
   - Per-strategy: G1/T1/D1 should each stay < ₹5,000
   - Global: Total should stay > -₹25,000

### Signal Observability

Use the new signal observability script:

```bash
bash scripts/query_signal_metrics.sh
```

This will show:
- Setups evaluated by OptionsRanker
- Filter rejections (IV, trend, RR, liquidity)
- Signals approved

---

## ⚠️ Risk Warnings

1. **Per-Strategy Loss Caps:** Each of G1, T1, D1 has a **₹5,000 daily loss cap**. If any strategy hits this cap, it should stop trading for the day.

2. **Global Loss Limit:** The **-₹25,000 hard stop** still applies. If total daily PnL reaches this, all trading stops.

3. **Position Limits:** Maximum **4 total positions** (1 per strategy). This is a hard cap.

4. **Margin Usage:** **30% margin cap** is unchanged. Monitor margin usage if multiple strategies are active simultaneously.

5. **Regime Dependencies:** G1, T1, D1 all require R1 regime classification. If R1 fails or misclassifies, these strategies may not trade.

---

## 🎯 Success Criteria for Day-4

### Minimum Viable Success

- ✅ All strategies load without errors
- ✅ R1 classifies regime correctly
- ✅ G1, T1, D1 appear in strategy list as enabled
- ✅ No config errors or import failures
- ✅ System remains stable with all strategies enabled

### Trading Success (Optional)

- At least 1 signal generated by G1, T1, or D1 (even if rejected by filters)
- If trades occur, positions appear correctly in both bot and Kite
- Per-strategy loss caps respected
- Global loss limit respected

### Failure Modes to Watch

- ❌ Strategy fails to load (check logs for import errors)
- ❌ R1 fails to classify regime (check market data connection)
- ❌ Strategy trades outside allowed regime (check R1 integration)
- ❌ Position count exceeds 4 (check position store)
- ❌ Daily loss exceeds per-strategy or global caps (check risk engine)

---

## 📝 Next Steps (Post Day-4)

1. **Review Day-4 Performance**
   - How many signals did G1/T1/D1 generate?
   - Which filters rejected most setups?
   - Did any strategy hit its daily loss cap?
   - Did regime classification match market conditions?

2. **Adjust if Needed (Day 5-7)**
   - If approval rate < 5% for 5-7 days → consider filter adjustments
   - If same filter blocks >70% of setups → consider widening that filter
   - If regime misclassification → review R1 thresholds

3. **Scale Up (Day 8+)**
   - If all strategies perform well for 7 days → consider:
     - Increasing lot sizes (1 → 2)
     - Increasing per-strategy capital (10% → 15%)
     - Widening entry windows

---

## ✅ Configuration Complete

All premium strategies (G1, T1, D1) are now enabled for Day-4 LIVE trading with **tiny, controlled risk limits**. The system is ready for Day-4 market open.

**Key Principle:** "Start small, measure everything, scale gradually."

---

**Generated:** 2025-11-19  
**Config Version:** Day-4 Premium Strategies Enabled

