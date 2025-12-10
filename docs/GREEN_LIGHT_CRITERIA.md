# Green-Light Criteria — Hard Gates for LIVE Scaling

**Purpose:** Define hard gates that must be consistently met before scaling LIVE risk.

**Principle:** These are **non-negotiable** safety checks. If any fail, stay in PAPER or tiny LIVE until resolved.

---

## 🟢 Pre-LIVE Gates (Must Pass for 10+ Consecutive PAPER Days)

### 1. Data Quality
- ✅ **No NaNs** in any key metric for 10 consecutive days
  - Check: `make sanity-check` shows all numeric values (no NaN/None)
  - Metrics: R1 features, G1 delta, T1/D1 ratios, Allocator weights, H1 coverage

### 2. R1 Regime Classification
- ✅ **R1 regimes visually align** with IV/ATR on at least **80–90% of days**
  - Check: Compare `algo_vol_regime_code` to your chart-based judgement
  - Low-vol grind → LOW_MEAN_REVERT
  - Panic/event days → HIGH_EVENT or CHAOTIC
  - If < 80% alignment → tune YAML thresholds

### 3. G1 Delta Hedging
- ✅ **G1 hedges consistently keep |Δ| under target** without excessive churn
  - Check: `gamma_scalper_abs_delta` stays near 0 after rebalance
  - Check: `gamma_scalper_rebalances` per day is reasonable (not 200+)
  - Target: |Δ| < configured threshold (e.g., 5–10 points) most of the time

### 4. Tail Coverage Discipline
- ✅ **Tail coverage never drops below minimum** when short-premium is non-zero
  - Check: `tail_short_vol_coverage_pct` ≥ `risk_budgets.min_coverage_pct` when `tail_short_vol_short_notional` > 0
  - If coverage drops → H1 logic is broken, fix before LIVE

### 5. Allocator Risk Limits
- ✅ **Allocator never allocates >X%** to any strategy in drawdown beyond Y%
  - Check: `allocator_final_weight` × `allocator_max_capital_pct` for strategies in drawdown
  - Example gate: No strategy > 40% capital if it's in > 10% drawdown
  - If violated → tighten `max_capital_pct_per_strategy` or add drawdown checks

---

## 🟡 Pre-Scaling Gates (Must Pass Before Increasing LIVE Size)

### 6. Strategy Performance Correlation
- ✅ **Allocator caps correlate with realized performance**
  - Check: Strategies with higher caps actually perform better
  - If mismatch → tune allocator scoring or base weights

### 7. Event Engine Behavior
- ✅ **H1 coverage and Allocator clearly adjust** on RBI/Budget/big US days
  - Check: `event_vol_engine_day_type` changes appropriately
  - Check: `tail_short_vol_coverage_pct` increases on PRE_EVENT/EVENT_DAY
  - If no adjustment → E1 integration is broken

### 8. Position Store Integrity
- ✅ **Position store PnL matches broker PnL** (within tolerance)
  - Check: Compare `position_store` aggregates to broker statements
  - Tolerance: ±0.1% of notional (or your risk tolerance)
  - If mismatch → position store logic needs fixing

### 9. Daily Loss Limits
- ✅ **Daily loss limits are respected** in PAPER
  - Check: System stops trading when daily loss limit hit
  - Check: No trades after limit exceeded
  - If violated → risk engine logic needs fixing

### 10. Execution Quality
- ✅ **Execution errors < 2 per day** for 10 consecutive days
  - Check: `trader_execution_errors_total` or equivalent
  - If > 2/day → order engine needs investigation

---

## 🔴 Hard Stops (Immediate Action Required)

If any of these occur, **stop trading immediately**:

- ❌ Leader lock lost (`trader_is_leader = 0`)
- ❌ Heartbeats stale (> 30 seconds)
- ❌ Daily loss limit hit
- ❌ Portfolio heat exceeded
- ❌ Execution errors (> 2 in a day)
- ❌ System errors detected
- ❌ Position store PnL mismatch > tolerance
- ❌ Tail coverage drops below minimum with active short positions

**Action:** Stop trading, investigate, fix, verify in PAPER before resuming.

---

## 📊 Weekly Review Checklist

Every weekend, verify all gates are still passing:

- [ ] Data quality: No NaNs for the week
- [ ] R1 alignment: > 80% regime accuracy
- [ ] G1 hedging: |Δ| controlled, reasonable churn
- [ ] H1 coverage: Never below minimum
- [ ] Allocator limits: No strategy exceeds caps
- [ ] Performance correlation: Caps match performance
- [ ] Event behavior: E1 influences H1/Allocator correctly
- [ ] Position store: PnL matches broker
- [ ] Loss limits: Respected in PAPER
- [ ] Execution: < 2 errors/day average

**If all pass → Safe to continue/scale LIVE gradually.**

**If any fail → Stay in PAPER/tiny LIVE until resolved.**

---

## 🎯 Scaling Path

1. **PAPER only** → All gates pass for 10+ days
2. **Tiny LIVE** (10–20% of target size) → All gates pass for 10+ days
3. **Gradual scale** (increase 10–20% per week) → Monitor gates continuously
4. **Target size** → Only when all gates consistently pass at each level

**Never skip steps. Each level must prove itself before moving up.**

