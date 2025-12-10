# Observation Checklist — Pass/Fail Sanity Checks

**Purpose:** Verify each refinement behaves as intended before scaling LIVE.

**Principle:** Fix **YAML thresholds**, not code, unless behavior is clearly broken.

---

## R1 — Regime Engine

**Goal:** Regime labels match your chart-based intuition.

### Metrics to Watch
- `algo_vol_regime_code{underlying}`
- `algo_vol_iv_rank{underlying}`
- `algo_vol_atr_pct{underlying}`
- `algo_vol_rv_iv_ratio{underlying}`
- `algo_vol_vix_rank{underlying}`

### Pass Criteria
- ✅ Low-vol grind days → `LOW_MEAN_REVERT`
- ✅ Panic/event days → `HIGH_EVENT` or `CHAOTIC`
- ✅ Regime labels generally agree with your visual judgement

### Fail → Fix
- If obvious HIGH_EVENT day shows LOW/MEDIUM → **tighten YAML thresholds** (`high_iv_rank`, `vix_extreme_rank`)
- If LOW_MEAN_REVERT never triggers → **loosen** `low_iv_rank`, `atr_pct_low`

---

## G1 — Gamma Scalper

**Goal:** Long gamma book stays near delta-neutral without excessive hedging.

### Metrics to Watch
- `gamma_scalper_abs_delta{underlying}` (before/after rebalance)
- `gamma_scalper_rebalances{underlying}` (count per day)
- `gamma_scalper_books_opened{underlying}`
- `gamma_scalper_books_closed{underlying}`

### Pass Criteria
- ✅ |Δ| gets pulled back **towards 0** after hedge cycles
- ✅ Rebalances **cluster** around bigger moves, not every tick
- ✅ Rebalance count per day is reasonable (not 200+ on normal days)

### Fail → Fix
- If machine-gun hedging → **tighten cooldown** or **raise delta threshold** in YAML
- If |Δ| stays large → **lower rebalance threshold** or check hedging logic

---

## T1 — Calendar Arb

**Goal:** Per-underlying bands actually change behavior.

### Metrics to Watch
- `calendar_arb_term_ratio{underlying}`
- `calendar_arb_term_spread{underlying}`
- `calendar_arb_books_opened{underlying}` (compare NIFTY vs BANKNIFTY)

### Pass Criteria
- ✅ When BANKNIFTY bands are looser than NIFTY → BANKNIFTY opens more calendars under similar conditions
- ✅ Entries align with visually obvious "weekly IV >> monthly IV" situations
- ✅ Strategy respects per-underlying thresholds

### Fail → Fix
- If no trades despite obvious term structure → **loosen** `term_ratio_min` in YAML
- If too many trades → **tighten** thresholds or raise `liquidity.min_oi`

---

## D1 — Dispersion Arb

**Goal:** FINNIFTY/MIDCAP pairs trade only when sector vs index actually diverge.

### Metrics to Watch
- `dispersion_arb_vol_ratio{parent="NIFTY",sector="FINNIFTY"}`
- `dispersion_arb_corr{parent="NIFTY",sector="FINNIFTY"}`
- `dispersion_arb_iv_ratio{parent="NIFTY",sector="FINNIFTY"}`
- Same for MIDCAP pairs
- `dispersion_arb_books_opened{parent,sector}`

### Pass Criteria
- ✅ Correlation is usually **positive and sensible** (0.5–0.9) except on weird days
- ✅ Vol ratio > 1 on days where sector visibly diverges from NIFTY
- ✅ Strategy doesn't open books on illiquid or junky days (liquidity filters working)

### Fail → Fix
- If FINNIFTY/MIDCAP too jumpy → **tighten** `corr_min` and `liquidity` thresholds in YAML
- If no trades despite obvious divergence → **loosen** `vol_ratio_min` or `iv_ratio_min`
- Consider keeping FINNIFTY/MIDCAP in **PAPER only** until stable

---

## Allocator (ML-Ready)

**Goal:** No surprises until ML has enough data.

### Configuration
- Keep `ml.enabled=false` OR run in **shadow mode** (log ML scores but use rule-based)

### Metrics to Watch
- `allocator_final_weight{strategy}`
- `allocator_max_capital_pct{strategy}`
- Strategy PnL vs allocated capital over weeks

### Pass Criteria
- ✅ Bad strategies get **down-weighted** over time
- ✅ No single strategy quietly dominates capital without matching performance
- ✅ Allocations correlate with realized performance

### Fail → Fix
- If one strategy creeps to 80% capital → **tighten** `max_capital_pct_per_strategy` in YAML
- If good strategies stay underweighted → **adjust** `base_weight` or scoring thresholds

### When ML is Ready
- Swap `ml.enabled=true` — plumbing is already safe, just changes score source

---

## H1 — Tail Short Vol Overlay

**Goal:** Tail coverage adjusts with regime and events.

### Metrics to Watch
- `tail_short_vol_short_notional{underlying}`
- `tail_short_vol_tail_notional{underlying}`
- `tail_short_vol_coverage_pct{underlying}`
- `tail_short_vol_adjustments{underlying}`

### Pass Criteria
- ✅ Coverage increases on HIGH_EVENT days (via E1 multiplier)
- ✅ Coverage scales with short premium notional
- ✅ Rebalances don't churn excessively

---

## E1 — Event Engine

**Goal:** Event calendar influences R1, Allocator, H1 appropriately.

### Metrics to Watch
- `event_vol_engine_day_type{underlying}` (NORMAL/PRE_EVENT/EVENT_DAY/POST_EVENT)
- `event_vol_engine_severity{underlying}`
- Observe behavior changes around RBI/Budget/US Fed days

### Pass Criteria
- ✅ Day type classification matches calendar dates
- ✅ H1 coverage multiplier increases on PRE_EVENT/EVENT_DAY
- ✅ Allocator role multipliers adjust appropriately

---

## What NOT to Do

❌ **Don't add more algos**  
❌ **Don't tweak code paths** unless metric/behavior is clearly wrong  
✅ **Only touch YAML thresholds/bands** and risk limits based on observations

---

## Success Criteria Before Scaling LIVE

All of these must be true for a stretch of PAPER + tiny LIVE:

1. ✅ R1 labels look sensible most days
2. ✅ G1 hedges keep |Δ| small without insane churn
3. ✅ T1 trades where term structure is obviously skewed
4. ✅ D1 only acts when sector vs index actually diverge
5. ✅ Allocator caps correlate with realized performance
6. ✅ Tail overlay + event engine clearly behave differently on RBI/Budget/big US days

**When all pass → You're running a desk, not troubleshooting.**

From here, any next "upgrade" is a **parameter/model change**, not a refactor.

