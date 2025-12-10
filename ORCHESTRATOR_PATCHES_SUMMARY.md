# Orchestrator Patches Summary - Day-4/5 Upgrade

**Date:** 2025-11-19  
**Status:** ✅ **ALL THREE PATCHES IMPLEMENTED**

---

## ✅ Patch 1: Token Limit & Safer Universe Handling

### Changes Made

**File:** `packages/core/orchestrator.py`

1. **Added configurable token limit** (line 101-108):
   ```python
   self.max_tokens_per_scan = int(
       os.getenv("MAX_TOKENS_PER_SCAN", "80")  # Default 80 (was hardcoded 20)
   )
   ```

2. **Updated `_scan_cycle()`** (lines 756-776):
   - Gets universe tokens
   - Applies configurable limit (default 80)
   - Logs universe size and tokens used
   - Handles empty universe gracefully

3. **New helper method `_run_strategy_on_tokens()`** (lines 679-730):
   - Centralized token iteration logic
   - Builds StrategyContext with regime/event data
   - Calls `strategy.generate_signals(context)`

### Configuration

Set environment variable:
```bash
export MAX_TOKENS_PER_SCAN=80  # Default, can increase to 120 once stable
```

### Impact

- **Before:** Only first 20 tokens scanned (starving strategies)
- **After:** Configurable limit (default 80, 4x improvement)
- **Future:** Can increase to 120+ once performance validated

---

## ✅ Patch 2: Strategy Priority Ordering

### Changes Made

**File:** `packages/core/orchestrator.py`

1. **New method `_sorted_strategies()`** (lines 667-677):
   ```python
   def _sorted_strategies(self) -> List[Strategy]:
       return sorted(
           self.strategies,
           key=lambda s: getattr(s, "priority", 100),
       )
   ```

2. **Updated `_scan_cycle()`** (line 801):
   - Uses `self._sorted_strategies()` instead of `self.strategies`
   - Premium strategies (lower priority number) run first

**File:** `apps/api/main.py`

3. **Priority assignment** (lines 485-500):
   - Reads priority from config (YAML)
   - Sets `strategy.priority` on instance
   - Defaults to 100 if not specified
   - Logs priorities at startup

### Configuration

**File:** `configs/kite_day1_live.yaml`

Priorities already configured:
- `RegimeVolEngine`: priority 0 (highest - runs first)
- `OptionsRanker`: priority 1
- `expiry_short_strangle_v2`: priority 2
- `intraday_short_strangle_v1`: priority 3
- `trend_credit_spread_v1`: priority 4
- `GammaScalper`: priority 4
- `CalendarArb`: priority 5
- `DispersionArb`: priority 6
- `TailShortVolOverlay`: priority 3

### Impact

- **Before:** Strategies run in list order (random)
- **After:** Premium strategies run first (R1 → OptionsRanker → Strangles → Credit Spreads)
- **Benefit:** Critical strategies get first access to market data

---

## ✅ Patch 3: Enriched StrategyContext (Regime + Event)

### Changes Made

**File:** `packages/core/strategies/base.py`

1. **Extended `StrategyContext`** (lines 30-34):
   ```python
   regime_snapshot: Optional[Dict[str, Any]] = None  # R1 output
   event_snapshot: Optional[Dict[str, Any]] = None   # E1 output
   universe_size: int = 0  # Total universe size
   token_count: int = 0    # Tokens being scanned
   ```

**File:** `packages/core/orchestrator.py`

2. **Regime/Event snapshot collection** (lines 778-796):
   - Gets R1 snapshot once per scan (if available)
   - Gets E1 snapshot once per scan (if available)
   - Handles errors gracefully

3. **Context enrichment** (lines 722-725):
   - Passes `regime_snapshot` to StrategyContext
   - Passes `event_snapshot` to StrategyContext
   - Includes `universe_size` and `token_count`

### Usage in Strategies

Strategies can now access regime/event data:

```python
def generate_signals(self, context: StrategyContext) -> List[Signal]:
    # Access regime
    if context.regime_snapshot:
        nifty_regime = context.regime_snapshot.get("NIFTY", {}).get("regime")
        if nifty_regime in ("HIGH_EVENT", "CHAOTIC"):
            return []  # Skip trading in chaotic regimes
    
    # Access event
    if context.event_snapshot:
        has_major_event = context.event_snapshot.get("today", {}).get("has_major_event", False)
        if has_major_event:
            return []  # Skip trading on event days
    
    # ... rest of strategy logic
```

### Impact

- **Before:** Strategies had to fetch regime/event data manually
- **After:** Regime/event data passed via context (zero refactor needed)
- **Benefit:** Consistent regime/event data across all strategies

---

## 🔍 Verification Checklist

### 1. Token Limit

Check logs for:
```
[Orchestrator] Scan cycle at ..., universe=400, using=80 tokens
```

Or set custom limit:
```bash
export MAX_TOKENS_PER_SCAN=120
```

### 2. Strategy Priority

Check startup logs:
```
Loaded 8 strategies: RegimeVolEngine(prio=0), OptionsRanker(prio=1), ...
```

Or query API:
```bash
curl -s http://localhost:8000/api/strategies/summary | jq '.strategies[] | {name, priority}'
```

Expected output:
```json
{"name":"RegimeVolEngine","priority":0}
{"name":"OptionsRanker","priority":1}
{"name":"expiry_short_strangle_v2","priority":2}
...
```

### 3. StrategyContext Enrichment

Add temporary logging in a strategy:
```python
def generate_signals(self, context: StrategyContext) -> List[Signal]:
    logger.info(
        f"[{self.name}] on_scan at {context.timestamp}, "
        f"regime={context.regime_snapshot.get('NIFTY',{}).get('regime') if context.regime_snapshot else 'NA'}, "
        f"event={context.event_snapshot.get('today',{}).get('has_major_event') if context.event_snapshot else 'NA'}"
    )
```

If this prints, context wiring is correct.

---

## 📊 Expected Behavior

### Before Patches

1. Only 20 tokens scanned per cycle
2. Strategies run in random order
3. Strategies must fetch regime/event data manually
4. No visibility into universe size

### After Patches

1. **80 tokens scanned per cycle** (configurable via `MAX_TOKENS_PER_SCAN`)
2. **Strategies run by priority** (R1 → OptionsRanker → Premium → Others)
3. **Regime/event data in context** (no manual fetching needed)
4. **Universe context available** (`universe_size`, `token_count`)

---

## 🚀 Next Steps

1. **Test in PAPER mode** to verify patches work correctly
2. **Monitor performance** - ensure 80 tokens doesn't slow down scan cycle
3. **Update strategies** to use `context.regime_snapshot` and `context.event_snapshot`
4. **Increase token limit** to 120 once stable (if needed)

---

## 📝 Files Modified

1. ✅ `packages/core/orchestrator.py` - Token limit, priority sorting, context enrichment
2. ✅ `packages/core/strategies/base.py` - Extended StrategyContext
3. ✅ `apps/api/main.py` - Priority assignment from config
4. ✅ `packages/core/instruments.py` - Fixed NetworkException import

---

**All three patches implemented and ready for testing!** 🎯

