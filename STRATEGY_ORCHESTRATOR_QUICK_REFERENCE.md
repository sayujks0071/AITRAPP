# Strategy Orchestrator - Quick Reference

## 🔄 Scan Cycle Flow

```
Every 5 seconds:
  _scan_supervisor()
    ↓
  _scan_cycle()
    ↓
  For each strategy (13 total):
    For each token (20 max):
      Build StrategyContext
      strategy.generate_signals(context)
    ↓
  Collect all signals
    ↓
  Rank signals (SignalRanker)
    ↓
  Risk check (RiskManager)
    ↓
  Execute top 3 opportunities
    ↓
  Monitor exits (ExitManager)
```

## 📋 Strategy List (Priority Order)

| Priority | Strategy | Type | Config |
|----------|----------|------|--------|
| 0 | RegimeVolEngine (R1) | Meta | `regime_vol_engine.yaml` |
| 1 | OptionsRanker | Primary | Inline |
| 2 | expiry_short_strangle | Secondary | Inline |
| 2 | expiry_short_strangle_v2 | Premium | `expiry_short_strangle_v2.yaml` |
| 3 | intraday_short_strangle_v1 | Premium | `intraday_short_strangle_v1.yaml` |
| 3 | TailShortVolOverlay (H1) | Overlay | `tail_short_vol.yaml` |
| 4 | trend_credit_spread_v1 | Premium | `trend_credit_spread_v1.yaml` |
| 4 | GammaScalper (G1) | Premium | `gamma_scalper.yaml` |
| 5 | CalendarArb (T1) | Premium | `calendar_arb.yaml` |
| 6 | DispersionArb (D1) | Premium | `dispersion_arb.yaml` |

## 🔴 Critical Issues

1. **Token Limit (20)** - Only first 20 tokens evaluated (universe has 400+)
2. **No Priority Ordering** - Strategies run in list order, not priority
3. **Missing Regime/Event in Context** - Strategies must fetch manually

## ⚠️ Important Issues

4. **Sequential Execution** - Not parallelized
5. **Massive if/elif Chain** - 13+ branches in main.py
6. **Allocator Runs Once** - Not periodic
7. **Missing Allocator Entries** - V2, Intraday, Trend not in allocator

## ✅ Quick Fixes

### Fix 1: Priority Ordering
```python
# In orchestrator._scan_cycle()
sorted_strategies = sorted(
    self.strategies,
    key=lambda s: getattr(s, 'priority', 999)
)
for strategy in sorted_strategies:
    # ...
```

### Fix 2: Enhance StrategyContext
```python
# In orchestrator._scan_cycle()
context = StrategyContext(
    # ... existing fields ...
    current_regime=self._get_current_regime(),  # From R1
    event_context=self._get_event_context(),    # From E1
)
```

### Fix 3: Increase Token Limit
```python
# In orchestrator._scan_cycle()
for token in universe_tokens[:50]:  # Increase from 20 to 50
    # ...
```

## 📊 Metrics to Monitor

- `orchestrator_scan_cycle_duration_seconds` - Should be < 5s
- `orchestrator_strategy_execution_time_seconds{strategy}` - Per-strategy timing
- `orchestrator_tokens_evaluated_total` - Track coverage
- `orchestrator_strategy_failures_total{strategy}` - Track failures

---

**Full Report:** See `STRATEGY_ORCHESTRATOR_ANALYSIS.md`

