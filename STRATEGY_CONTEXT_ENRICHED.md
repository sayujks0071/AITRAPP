# StrategyContext & Strategy Base Class - Enriched Implementation

**Date:** 2025-11-19  
**Status:** ✅ **HYBRID IMPLEMENTATION COMPLETE**

---

## Overview

Extended `StrategyContext` and `Strategy` base class to support **both legacy and new formats**, ensuring:
- ✅ **Backward compatibility** with existing strategies
- ✅ **Forward compatibility** with StatGeist-style patterns
- ✅ **Zero breaking changes** to existing code

---

## StrategyContext - Hybrid Structure

### Legacy Fields (Backward Compatible)

Existing strategies continue to work with:
- `timestamp: datetime`
- `instrument: Instrument` (single instrument)
- `latest_tick: Optional[Tick]`
- `bars_1s: List[Bar]`
- `bars_5s: List[Bar]`
- `net_liquid: float`
- `available_margin: float`
- `open_positions: int`
- `iv_percentile: Optional[float]`
- `oi_change_pct: Optional[float]`

### New Fields (StatGeist-Style)

New strategies can use:
- `ltp: Dict[str, float]` - Last traded prices by symbol
- `ohlc: Dict[str, Any]` - OHLC data by symbol
- `positions: List[Any]` - List of Position objects
- `margins: Dict[str, float]` - Margin data (net_liquid, available_margin, used_margin, margin_usage_pct)

### Enriched Context (Patch 3)

- `regime_snapshot: Optional[Dict[str, Any]]` - Full R1 output
- `regime: Optional[str]` - Simplified regime string (auto-extracted)
- `event_snapshot: Optional[Dict[str, Any]]` - E1 output
- `universe_size: int` - Total universe size
- `token_count: int` - Tokens being scanned

### Helper Properties

```python
context.is_event_day  # bool - True if today is an event day
context.event_impact  # str - "LOW", "MEDIUM", "HIGH"
```

---

## Strategy Base Class - Enhanced

### New `__init__` Signature

```python
def __init__(self, name: str, params: Dict[str, Any], priority: Optional[int] = None):
    # Priority can be:
    # 1. Passed directly: Strategy("name", params, priority=10)
    # 2. From params: Strategy("name", {"priority": 10, ...})
    # 3. Default: 100 if not specified
```

### New Methods

1. **`async def execute(context: StrategyContext) -> List[Signal]`**
   - Optional async execution method
   - Default: calls `generate_signals()` for backward compatibility
   - New strategies can override for async/await support

2. **`async def on_tick(tick_data: Any) -> None`**
   - Optional real-time tick handling
   - Default: no-op
   - Useful for high-frequency strategies

### Backward Compatibility

Existing strategies work unchanged:
```python
class MyStrategy(Strategy):
    def __init__(self, name: str, params: Dict[str, Any]):
        super().__init__(name, params)  # priority defaults to 100
    
    def generate_signals(self, context: StrategyContext) -> List[Signal]:
        # Can still use context.latest_tick, context.instrument, etc.
        return []
```

---

## Orchestrator Integration

The orchestrator now populates **both formats**:

### Legacy Format (Per-Instrument)
```python
context = StrategyContext(
    timestamp=current_time,
    instrument=instrument,  # Single instrument
    latest_tick=tick,       # Tick object
    bars_5s=bars_5s,         # Bar objects
    net_liquid=1000000.0,
    available_margin=700000.0,
    ...
)
```

### New Format (Multi-Instrument Dicts)
```python
context = StrategyContext(
    # ... legacy fields ...
    ltp={"NIFTY": 24000.0, "NIFTY 50": 24000.0},  # Dict-based
    ohlc={"NIFTY": {"open": 23900, "high": 24100, ...}},  # Dict-based
    positions=[...],  # List of Position objects
    margins={"net_liquid": 1000000.0, "available_margin": 700000.0, ...},
    ...
)
```

### Regime/Event Enrichment
```python
context = StrategyContext(
    # ... other fields ...
    regime_snapshot={"NIFTY": {"regime": "LOW_MEAN_REVERT", ...}},  # Full dict
    regime="LOW_MEAN_REVERT",  # Simplified string (auto-extracted)
    event_snapshot={"today": {"is_event_day": False, "impact": "LOW"}},
    universe_size=400,
    token_count=80
)
```

---

## Usage Examples

### Example 1: Legacy Strategy (Backward Compatible)

```python
class OptionsRanker(Strategy):
    def generate_signals(self, context: StrategyContext) -> List[Signal]:
        # Uses legacy format
        if not context.latest_tick:
            return []
        
        instrument = context.instrument
        price = context.latest_tick.last_price
        
        # Can also use new fields if needed
        if context.regime == "HIGH_EVENT":
            return []  # Skip in high event regime
        
        return [Signal(...)]
```

### Example 2: New Strategy (StatGeist-Style)

```python
class NewStrategy(Strategy):
    async def execute(self, context: StrategyContext) -> List[Signal]:
        # Uses new format
        nifty_price = context.ltp.get("NIFTY")
        if not nifty_price:
            return []
        
        # Check regime
        if context.regime in ("HIGH_EVENT", "CHAOTIC"):
            return []
        
        # Check event
        if context.is_event_day and context.event_impact == "HIGH":
            return []
        
        # Access positions
        open_positions = [p for p in context.positions if p.is_open]
        
        # Access margins
        margin_usage = context.margins.get("margin_usage_pct", 0.0)
        if margin_usage > 30.0:
            return []
        
        return [Signal(...)]
```

### Example 3: Hybrid Strategy (Uses Both)

```python
class HybridStrategy(Strategy):
    def generate_signals(self, context: StrategyContext) -> List[Signal]:
        # Legacy: Single instrument focus
        instrument = context.instrument
        tick = context.latest_tick
        
        # New: Multi-instrument data
        all_prices = context.ltp  # Dict of all prices
        
        # New: Regime/event
        if context.regime == "LOW_MEAN_REVERT":
            # Use legacy bars for analysis
            bars = context.bars_5s
            # ... analysis ...
        
        return [Signal(...)]
```

---

## Migration Path

### Phase 1: Current (✅ Complete)
- Extended `StrategyContext` with new fields
- Orchestrator populates both formats
- Existing strategies work unchanged

### Phase 2: Gradual Migration (Future)
- New strategies use `execute()` and dict-based format
- Existing strategies continue using `generate_signals()` and object-based format
- Both patterns coexist

### Phase 3: Full Migration (Future)
- All strategies migrated to new format
- Legacy fields deprecated (but still supported)
- Cleaner, more consistent codebase

---

## Benefits

1. **Zero Breaking Changes**: All existing strategies work unchanged
2. **Flexible**: Strategies can use either format (or both)
3. **Future-Proof**: New strategies can adopt StatGeist patterns
4. **Gradual Migration**: No big-bang refactor needed
5. **Rich Context**: Regime/event data available to all strategies

---

## Verification

✅ All patches verified:
- Patch 1: Token limit (80 default)
- Patch 2: Priority ordering (strategies sorted correctly)
- Patch 3: Enriched context (regime/event available)

✅ Backward compatibility verified:
- Existing strategies work with old signature
- New strategies can use new signature
- Priority can come from params or direct argument

✅ New features verified:
- `ltp` and `ohlc` dicts populated
- `positions` and `margins` dicts populated
- `regime` string auto-extracted
- Helper properties (`is_event_day`, `event_impact`) work

---

**Status: Production Ready** 🎯

All three patches implemented with backward compatibility maintained!

