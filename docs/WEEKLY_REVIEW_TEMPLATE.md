# Weekly Review Template

**Purpose:** One-page weekly review to close the loop between your desk and your brain.

**When:** Every weekend (Saturday/Sunday)

**Time:** ~15 minutes

---

## Week of: _______________

### 📊 Strategy Performance

| Strategy | PnL | Allocator Weight | Max Capital % | Notes |
|----------|-----|-----------------|---------------|-------|
| R1 (Regime) | | | | |
| G1 (Gamma) | | | | |
| T1 (Calendar) | | | | |
| D1 (Dispersion) | | | | |

**Best Performer:** _______________

**Worst Performer:** _______________

**Action Items:**
- [ ] Tune allocator weights for underperformers?
- [ ] Adjust strategy-specific thresholds?

---

### 🎯 Regime Distribution

| Regime | Days | % of Week | Avg PnL | Notes |
|--------|------|-----------|---------|-------|
| LOW_MEAN_REVERT | | | | |
| MEDIUM_TREND | | | | |
| HIGH_EVENT | | | | |
| CHAOTIC | | | | |

**Observations:**
- Did regimes match market conditions? (Y/N)
- Any regime misclassifications? (List dates)
- Action: Tune R1 thresholds? (Y/N)

---

### 🛡️ Tail Coverage Analysis

**Average Coverage %:** _______________

**Coverage on Event Days:** _______________

**Tail Costs vs Protection:**
- Total tail premium paid: _______________
- Largest tail payout (if any): _______________
- Net tail cost: _______________

**Observations:**
- Did coverage adjust appropriately on event days? (Y/N)
- Are tail costs reasonable? (Y/N)
- Action: Adjust H1 targets? (Y/N)

---

### 🎚️ Allocator Behavior

**Did caps correlate with performance?** (Y/N)

**Any strategy exceed caps?** (Y/N) If yes, which: _______________

**Allocator adjustments made:**
- [ ] Base weights changed
- [ ] Max capital % adjusted
- [ ] Scoring thresholds tuned
- [ ] None

**Observations:**
- Did good strategies get more capital? (Y/N)
- Did bad strategies get cut? (Y/N)
- Action: Further tuning needed? (Y/N)

---

### 📅 Event Engine Impact

**Major Events This Week:**
- [ ] RBI Policy
- [ ] Budget
- [ ] US Fed
- [ ] CPI Release
- [ ] Elections
- [ ] Other: _______________

**Did E1 influence behavior?** (Y/N)
- H1 coverage increased on event days? (Y/N)
- Allocator adjusted role multipliers? (Y/N)
- R1 regime bias applied? (Y/N)

**Observations:**
- Did event-driven adjustments make sense? (Y/N)
- Action: Update event calendar or multipliers? (Y/N)

---

### 🔧 YAML Tweaks Made This Week

| Date | Config | Change | Reason |
|------|--------|--------|--------|
| | | | |
| | | | |
| | | | |

**Total Config Changes:** _______________

**Were changes effective?** (Y/N)

---

### ✅ Green-Light Criteria Check

Review `docs/GREEN_LIGHT_CRITERIA.md`:

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

**All gates passing?** (Y/N)

**If NO, which gates failed:** _______________

**Action:** Stay in PAPER/tiny LIVE until resolved? (Y/N)

---

### 🤖 MCP Config Suggestions

**Friday EOD - Run:**
```
Using propose_config_tweaks with 30-day window,
suggest allocator weight changes.
```

**Suggestions Received:**
- _______________
- _______________
- _______________

**Applied?** (Y/N) If yes, commit with: `make commit-configs MSG="..."`

---

### 🎯 Next Week Priorities

1. _______________
2. _______________
3. _______________

---

### 📝 Notes & Observations

(Free-form notes about the week, anomalies, insights, etc.)

---

**Review Completed By:** _______________

**Date:** _______________

---

## Quick Reference

- **Daily Reports:** `reports/daily/YYYY-MM-DD_report.md`
- **Sanity Checks:** `make sanity-check`
- **Configs:** `configs/*.yaml`
- **Green-Light Criteria:** `docs/GREEN_LIGHT_CRITERIA.md`
- **Observation Checklist:** `docs/OBSERVATION_CHECKLIST.md`

