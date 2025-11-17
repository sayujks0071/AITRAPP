# Full-Desk PAPER Playbook - Next 5-10 Trading Days

## Overview

This playbook guides you through running the **complete vol desk** in PAPER mode for the next 5-10 trading days. The goal is to **observe and build intuition** about how all components work together before going LIVE.

---

## Pre-Open Checklist (8:45 - 9:10 IST)

### 1. Infrastructure Startup

```bash
# Start API server
make live  # or your startup command

# Verify health
curl http://localhost:8000/health
curl http://localhost:8000/state
curl http://localhost:8000/ready
```

**Required state:**
- `/health` → `200 OK`
- `/state` → `mode: "LIVE"` (or "PAPER" if in paper mode)
- `/ready` → `200 OK`, `ready: true`
- Leader lock = `1` (trader_is_leader = 1.0)
- All heartbeats < 5s
- Scan ticks increasing

### 2. Strategy Verification

Run all verification scripts:

```bash
make verify-r1   # Regime engine
make verify-g1   # Gamma scalper
make verify-t1   # Calendar arb
make verify-d1   # Dispersion arb
make verify-h1   # Tail overlay
make verify-allocator  # Capital allocator
```

**Expected:**
- All strategies loaded
- Configs present
- Metrics endpoints accessible

### 3. Allocator Setup (Observe Mode)

**Option A: Observe only (recommended first week)**
- Let allocator compute caps
- Log them to console/metrics
- Don't enforce in risk engine yet

**Option B: Soft enforcement**
- Set `global_max_capital_pct: 0.15` (very low)
- Per-strategy caps: 1-2% each
- Monitor if strategies hit caps

### 4. H1 Tail Overlay Setup

**Conservative settings:**
```yaml
target_tail_coverage_pct: 0.10  # Start low
min_tail_coverage_pct: 0.08
max_tail_coverage_pct: 0.15
```

**Mode:**
- Observe mode first (calculate but don't trade)
- Or enable with tiny size

---

## During Market Hours - Dashboard Focus

### Key Metrics to Monitor

#### 1. Regime Layer (R1)

**Primary metrics:**
```promql
algo_vol_regime_code{underlying="NIFTY"}
algo_vol_regime_code{underlying="BANKNIFTY"}
algo_vol_iv_rank{underlying="NIFTY"}
algo_vol_atr_pct{underlying="NIFTY"}
```

**What to watch:**
- Current regime (LOW_MEAN_REVERT / MEDIUM_TREND / HIGH_EVENT / CHAOTIC)
- Regime switches during the day
- IV rank and ATR trends

**Expected patterns:**
- **Quiet days:** LOW_MEAN_REVERT or MEDIUM_TREND
- **Event days:** HIGH_EVENT or CHAOTIC
- **Volatile days:** HIGH_EVENT, IV rank spikes

#### 2. Strategy Activity

**G1 (Gamma Scalper):**
```promql
gamma_scalper_books_opened{underlying="NIFTY"}
gamma_scalper_abs_delta{underlying="NIFTY"}
gamma_scalper_rebalances{underlying="NIFTY"}
gamma_scalper_pnl_pct{underlying="NIFTY"}
```

**T1 (Calendar Arb):**
```promql
calendar_arb_term_ratio{underlying="NIFTY"}
calendar_arb_term_spread{underlying="NIFTY"}
calendar_arb_books_opened{underlying="NIFTY"}
calendar_arb_pnl_pct{underlying="NIFTY"}
```

**D1 (Dispersion Arb):**
```promql
dispersion_arb_vol_ratio{parent="NIFTY", sector="BANKNIFTY"}
dispersion_arb_corr{parent="NIFTY", sector="BANKNIFTY"}
dispersion_arb_books_opened{parent="NIFTY", sector="BANKNIFTY"}
dispersion_arb_pnl_pct{parent="NIFTY", sector="BANKNIFTY"}
```

**What to watch:**
- Books opening/closing
- PnL trends
- Strategy behavior vs regime

#### 3. Allocator Decisions

```promql
allocator_final_weight{strategy=~".*"}
allocator_max_capital_pct{strategy=~".*"}
allocator_enabled{strategy=~".*"}
allocator_raw_score{strategy=~".*"}
```

**What to watch:**
- Which strategies get higher weights
- Which strategies get cut (enabled=0)
- Weight changes during the day
- Correlation with actual performance

#### 4. Tail Overlay (H1)

```promql
tail_short_vol_short_notional{underlying="NIFTY"}
tail_short_vol_tail_notional{underlying="NIFTY"}
tail_short_vol_coverage_pct{underlying="NIFTY"}
tail_short_vol_adjustments{underlying="NIFTY"}
```

**What to watch:**
- Coverage percentage
- Adjustments triggered
- Coverage changes with regime
- Short notional vs tail notional

---

## Expected Patterns (Build Intuition)

### Quiet Day (LOW_MEAN_REVERT)

**Regime:**
- R1: LOW_MEAN_REVERT or MEDIUM_TREND
- IV rank: 20-40%
- ATR: Low

**Strategies:**
- G1: Mostly idle (not in allowed regimes or conditions not met)
- T1: May open if term structure favorable
- D1: May open if dispersion present
- Short vol strategies: Active (allocator favors them)

**H1:**
- Coverage: ~10-15% (normal multiplier)
- Few adjustments

**Allocator:**
- Boosts: income_short_vol, directional_income
- Cuts: long_vol, long_gamma

### Event Day (HIGH_EVENT)

**Regime:**
- R1: HIGH_EVENT or CHAOTIC
- IV rank: 60-80%+
- ATR: High

**Strategies:**
- G1: May open (allowed in HIGH_EVENT)
- T1: May open (term structure often favorable)
- D1: May open (dispersion common)
- Short vol strategies: Reduced (allocator cuts them)

**H1:**
- Coverage: ~20-30% (multiplier 1.5x-2.0x)
- More adjustments

**Allocator:**
- Boosts: long_vol, long_gamma, term_structure
- Cuts: income_short_vol

### Volatile Day (CHAOTIC)

**Regime:**
- R1: CHAOTIC
- IV rank: 80%+
- ATR: Very high

**Strategies:**
- G1: May open (allowed)
- T1: May stay flat (too risky)
- D1: May stay flat (correlation may break)
- Short vol strategies: Mostly disabled

**H1:**
- Coverage: ~30% (2.0x multiplier)
- Frequent adjustments

**Allocator:**
- Boosts: long_vol, long_gamma only
- Cuts: Most others

---

## Post-Close Daily Report

### Generate Daily Summary

Create a script or manual process to dump:

**1. Strategy Performance:**
```json
{
  "date": "2025-01-15",
  "strategies": {
    "gamma_scalper": {
      "trades": 2,
      "wins": 1,
      "losses": 1,
      "pnl": 1500.0,
      "hit_rate": 0.5,
      "max_drawdown": 500.0
    },
    "calendar_arb": {
      "trades": 1,
      "wins": 1,
      "losses": 0,
      "pnl": 800.0,
      "hit_rate": 1.0,
      "max_drawdown": 0.0
    }
  }
}
```

**2. Allocator Decisions:**
```json
{
  "allocations": {
    "gamma_scalper": {
      "raw_score": 0.78,
      "final_weight": 0.22,
      "max_capital_pct": 0.13,
      "enabled": true
    }
  }
}
```

**3. Tail Coverage Profile:**
```json
{
  "tail_coverage": {
    "NIFTY": {
      "avg_coverage_pct": 12.5,
      "min_coverage_pct": 10.0,
      "max_coverage_pct": 18.0,
      "adjustments": 3
    }
  }
}
```

**4. Regime Timeline:**
```json
{
  "regime_timeline": [
    {"time": "09:30", "regime": "MEDIUM_TREND"},
    {"time": "11:00", "regime": "HIGH_EVENT"},
    {"time": "14:00", "regime": "MEDIUM_TREND"}
  ]
}
```

### Review Questions

After each day, ask:

1. **Did regime classification make sense?**
   - Did R1 correctly identify quiet vs event days?
   - Did regime switches align with market events?

2. **Did strategies behave as expected?**
   - Did G1 open in allowed regimes?
   - Did T1 open when term structure was favorable?
   - Did D1 open when dispersion was present?

3. **Did allocator make good decisions?**
   - Did good strategies get higher weights?
   - Did bad strategies get cut?
   - Were allocations stable or too volatile?

4. **Did H1 provide protection?**
   - Did coverage adjust with regime?
   - Were adjustments reasonable?
   - Did tail costs seem reasonable?

5. **Any surprises?**
   - Unexpected behavior?
   - Metrics that don't make sense?
   - Strategies that should have traded but didn't?

---

## Week 1 Goals

**Days 1-2:**
- Get all systems running
- Verify all metrics populate
- Build basic dashboards

**Days 3-5:**
- Observe regime behavior
- Watch strategy activity
- Note patterns

**Days 6-7:**
- Review first week
- Identify tuning opportunities
- Plan adjustments

---

## Week 2 Goals

**Days 8-10:**
- Refine thresholds based on observations
- Tune allocator weights
- Adjust H1 coverage targets
- Prepare for small LIVE test

---

## Troubleshooting

### No Strategy Activity

1. **Check regime:**
   ```bash
   curl http://localhost:8000/metrics | grep algo_vol_regime_code
   ```
   - May be in disallowed regime
   - May need to adjust allowed regimes

2. **Check thresholds:**
   - IV rank may be out of range
   - Term structure may not be favorable
   - Correlation may be too low

3. **Check entry windows:**
   - Strategies may only trade in specific time windows
   - Check configs for entry_window settings

### Metrics Not Populating

1. **Check if strategies are loaded:**
   ```bash
   curl http://localhost:8000/state | jq '.strategies'
   ```

2. **Check logs:**
   ```bash
   tail -f /tmp/kite_api_live.log | grep -i "strategy\|regime\|allocator"
   ```

3. **Check if market data is flowing:**
   ```bash
   curl http://localhost:8000/metrics | grep trader_scan_ticks_total
   ```

### Unexpected Behavior

1. **Review configs:**
   - Thresholds may be too strict/loose
   - Entry windows may be wrong
   - Regime overlays may need adjustment

2. **Check logs for errors:**
   ```bash
   grep -i "error\|exception\|failed" /tmp/kite_api_live.log | tail -20
   ```

3. **Compare with expected patterns:**
   - Review this playbook's expected patterns
   - Check if behavior matches regime

---

## Success Criteria (End of Week 2)

You're ready to move to small LIVE when:

1. ✅ All systems running smoothly
2. ✅ Metrics populate correctly
3. ✅ Regime classification makes sense
4. ✅ Strategies behave as expected
5. ✅ Allocator decisions seem reasonable
6. ✅ H1 coverage adjusts with regime
7. ✅ No major surprises or errors
8. ✅ Daily reports show consistent patterns

---

## Next Steps After PAPER

Once PAPER behavior looks sane:

1. **Small LIVE test** (see `LIVE_ROLLOUT_PLAN.md`)
2. **Position store integration** (wire real PnL tracking)
3. **Threshold tuning** (based on observations)
4. **Event calendar** (E1 - optional next module)

---

## Daily Checklist Template

```
Date: ___________

Pre-Open:
[ ] Infrastructure healthy
[ ] All verifications pass
[ ] Allocator in observe mode
[ ] H1 configured conservatively

During Market:
[ ] Regime metrics monitored
[ ] Strategy activity tracked
[ ] Allocator decisions logged
[ ] H1 coverage observed

Post-Close:
[ ] Daily report generated
[ ] Patterns reviewed
[ ] Issues noted
[ ] Adjustments planned
```


