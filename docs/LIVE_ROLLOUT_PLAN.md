# LIVE Rollout Plan - Extremely Conservative Approach

## Overview

This plan guides the transition from PAPER to LIVE trading. The approach is **extremely conservative** - start tiny, verify everything, then scale slowly.

**Key principle:** Only move to LIVE when PAPER behavior is completely understood and predictable.

---

## Prerequisites (Must Complete First)

### 1. PAPER Validation Complete

- ✅ 5-10 trading days in PAPER
- ✅ All systems running smoothly
- ✅ Metrics populate correctly
- ✅ Regime classification makes sense
- ✅ Strategies behave as expected
- ✅ Allocator decisions reasonable
- ✅ H1 coverage adjusts correctly
- ✅ Daily reports show consistent patterns

### 2. Position Store Wired

- ✅ Position store integrated
- ✅ PnL tracking accurate
- ✅ Notional calculations correct
- ✅ Stats engine using real data

### 3. Risk Controls Verified

- ✅ Daily loss limits working
- ✅ Portfolio heat limits working
- ✅ Per-trade risk limits working
- ✅ Strategy caps enforced

---

## Phase 1: Single Strategy + H1 (Week 1)

### Strategy Selection

**Start with ONE short-vol income strategy:**
- `expiry_short_strangle` OR
- `intraday_short_strangle` OR
- `vscore_credit_spread`

**Why short-vol first:**
- More predictable
- Easier to understand
- H1 provides protection
- Lower capital requirements

### Configuration

**Allocator:**
```yaml
global_max_capital_pct: 0.15  # Very low
strategies:
  - name: "expiry_short_strangle"
    base_weight: 1.0  # Only this strategy
    # ... others disabled or weight 0
```

**H1:**
```yaml
target_tail_coverage_pct: 0.10  # Conservative
min_tail_coverage_pct: 0.08
max_tail_coverage_pct: 0.12
```

**Strategy:**
- 1 lot only
- Max 1 position at a time
- Tight risk limits

### Monitoring

**Watch closely:**
- Every trade execution
- Fill prices vs expected
- Slippage
- Margin usage
- PnL vs expected

**Daily checks:**
- Real PnL matches expected
- Tail hedges executing
- No unexpected behavior

### Success Criteria

Move to Phase 2 when:
- ✅ 5+ successful trades
- ✅ PnL matches expectations
- ✅ No execution issues
- ✅ Tail hedges working
- ✅ Risk limits respected

---

## Phase 2: Add Second Strategy (Week 2)

### Add Another Short-Vol Strategy

**Options:**
- Add `intraday_short_strangle` OR
- Add `vscore_credit_spread`

**Configuration:**
```yaml
global_max_capital_pct: 0.20  # Slightly higher
strategies:
  - name: "expiry_short_strangle"
    base_weight: 0.6
  - name: "intraday_short_strangle"
    base_weight: 0.4
```

**H1:**
- Same conservative settings
- Monitor coverage across both strategies

### Monitoring

**Watch:**
- Both strategies trading
- Allocator splitting capital
- H1 covering both
- No conflicts

---

## Phase 3: Enable Allocator (Week 3)

### Full Allocator Control

**Configuration:**
```yaml
global_max_capital_pct: 0.30  # Still conservative
strategies:
  # All short-vol strategies enabled
  - name: "expiry_short_strangle"
    base_weight: 0.30
  - name: "intraday_short_strangle"
    base_weight: 0.20
  - name: "vscore_credit_spread"
    base_weight: 0.20
  - name: "drifting_credit_spread"
    base_weight: 0.15
  # Long vol strategies still disabled or tiny
```

**Allocator:**
- Enforce caps
- Monitor weight changes
- Watch for strategy cuts

### Monitoring

**Watch:**
- Allocator decisions
- Weight changes
- Strategy enable/disable
- Performance vs allocations

---

## Phase 4: Add Long Vol Strategies (Week 4+)

### Enable G1, T1, D1

**One at a time:**
- Week 4: Enable G1 (gamma scalper)
- Week 5: Enable T1 (calendar arb)
- Week 6: Enable D1 (dispersion arb)

**Configuration:**
```yaml
global_max_capital_pct: 0.40  # Gradually increasing
strategies:
  # Short vol
  - name: "expiry_short_strangle"
    base_weight: 0.20
  # ... other short vol
  
  # Long vol (one at a time)
  - name: "gamma_scalper"
    base_weight: 0.10  # Start small
```

**H1:**
- Monitor coverage
- Adjust if needed

### Monitoring

**Watch:**
- Long vol strategies trading
- Interaction with short vol
- H1 coverage adequacy
- Overall portfolio risk

---

## Phase 5: Scale Up (Month 2+)

### Gradually Increase Size

**Only if:**
- All strategies stable
- PnL positive
- Risk limits respected
- No execution issues

**Increments:**
- Week 1: `global_max_capital_pct: 0.40`
- Week 2: `global_max_capital_pct: 0.50`
- Week 3: `global_max_capital_pct: 0.60` (target)

**Per-strategy:**
- Start: 1 lot
- After 10 successful trades: 2 lots
- After 20 successful trades: 3 lots (if stable)

### Monitoring

**Watch:**
- Slippage at larger sizes
- Margin usage
- Execution quality
- PnL scalability

---

## Risk Limits Throughout

### Never Exceed

- **Daily loss limit:** -2% of capital (very tight)
- **Portfolio heat:** 2% max
- **Per-trade risk:** 0.5% max
- **Strategy caps:** As set by allocator

### Circuit Breakers

**Auto-disable if:**
- Daily loss > -1.5%
- 3 consecutive losses
- Execution errors > 2 in a day
- System errors detected

---

## Daily LIVE Checklist

```
Pre-Open:
[ ] All systems healthy
[ ] Risk limits set
[ ] Position store ready
[ ] Allocator configured
[ ] H1 configured

During Market:
[ ] Monitor every trade
[ ] Check fills vs expected
[ ] Verify risk limits
[ ] Watch tail coverage
[ ] Monitor allocator

Post-Close:
[ ] Review all trades
[ ] Check PnL accuracy
[ ] Verify risk limits
[ ] Review tail costs
[ ] Plan next day
```

---

## Red Flags - Stop Trading If

1. **Execution issues:**
   - Slippage > 2x expected
   - Fill delays > 30s
   - Order rejections

2. **PnL discrepancies:**
   - Real PnL vs expected > 20%
   - Unexplained losses
   - Position tracking errors

3. **Risk limit breaches:**
   - Daily loss limit hit
   - Portfolio heat exceeded
   - Strategy caps exceeded

4. **System errors:**
   - Leader lock lost
   - Heartbeats stale
   - Data feed issues

**When red flag occurs:**
- **Immediately:** Stop trading
- **Investigate:** Root cause
- **Fix:** Before resuming
- **Verify:** In PAPER first

---

## Success Metrics

### Week 1-2 (Single Strategy)

- ✅ 10+ successful trades
- ✅ PnL within 10% of expected
- ✅ No execution issues
- ✅ Tail hedges working
- ✅ Risk limits respected

### Week 3-4 (Allocator)

- ✅ Allocator making good decisions
- ✅ Weights stable
- ✅ Performance matches allocations
- ✅ No strategy conflicts

### Month 2+ (Full Stack)

- ✅ All strategies trading
- ✅ Overall PnL positive
- ✅ Risk-adjusted returns good
- ✅ System stable
- ✅ Ready to scale

---

## Scaling Decision Tree

```
Can I increase size?
├─ Yes, if:
│  ├─ 10+ successful trades at current size
│  ├─ PnL positive and consistent
│  ├─ No execution issues
│  ├─ Risk limits never hit
│  └─ System stable
│
└─ No, if:
   ├─ Any red flags
   ├─ PnL inconsistent
   ├─ Execution issues
   ├─ Risk limits hit
   └─ System unstable
```

---

## Emergency Procedures

### If Daily Loss Limit Hit

1. **Immediately stop trading**
2. **Review all positions**
3. **Close if necessary**
4. **Investigate cause**
5. **Fix before resuming**

### If System Error

1. **Stop trading**
2. **Check logs**
3. **Restart if needed**
4. **Verify in PAPER first**
5. **Resume only when stable**

### If Execution Issue

1. **Stop trading**
2. **Check broker connection**
3. **Verify orders**
4. **Reconcile positions**
5. **Resume when fixed**

---

## Post-LIVE Review (After Each Phase)

### Questions to Answer

1. **Did execution match expectations?**
   - Fills, slippage, latency

2. **Did PnL match expected?**
   - Real vs paper PnL

3. **Did risk limits work?**
   - Were they hit? Too tight/loose?

4. **Did strategies behave correctly?**
   - Same as PAPER?

5. **Did H1 provide protection?**
   - Coverage adequate? Costs reasonable?

6. **Any surprises?**
   - Unexpected behavior? Issues?

### Adjustments

Based on review:
- Tune thresholds
- Adjust risk limits
- Refine allocator
- Update H1 coverage
- Fix any issues

---

## Timeline Summary

- **Week 1:** Single strategy + H1
- **Week 2:** Add second strategy
- **Week 3:** Enable allocator
- **Week 4:** Add G1
- **Week 5:** Add T1
- **Week 6:** Add D1
- **Month 2:** Scale up gradually

**Total:** ~2 months to full stack at target size

---

## Key Principles

1. **Start tiny** - 1 lot, 1 strategy
2. **Verify everything** - Every trade, every metric
3. **Scale slowly** - Only after proven success
4. **Monitor closely** - Watch every trade initially
5. **Stop if unsure** - Better safe than sorry
6. **Fix before resume** - Never trade with known issues

---

## Next Steps After Full LIVE

Once full stack is LIVE and stable:

1. **Optimize** - Tune thresholds, weights, coverage
2. **Scale** - Increase size gradually
3. **Add E1** - Event calendar (optional)
4. **Enhance** - Better Greeks, ML allocator, etc.


