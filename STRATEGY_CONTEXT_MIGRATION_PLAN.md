# StrategyContext Migration Plan

## Current vs Proposed Structure

### Current Structure (AITRAPP)
```python
@dataclass
class StrategyContext:
    timestamp: datetime
    instrument: Instrument  # Single instrument per context
    
    # Market data
    latest_tick: Optional[Tick] = None
    bars_1s: List[Bar] = None
    bars_5s: List[Bar] = None
    
    # Portfolio state
    net_liquid: float = 0.0
    available_margin: float = 0.0
    open_positions: int = 0
    
    # Market regime
    iv_percentile: Optional[float] = None
    oi_change_pct: Optional[float] = None
    
    # Patch 3: Enriched
    regime_snapshot: Optional[Dict[str, Any]] = None
    event_snapshot: Optional[Dict[str, Any]] = None
    universe_size: int = 0
    token_count: int = 0
```

### Proposed Structure (User's Blueprint)
```python
@dataclass
class StrategyContext:
    # Market Data (dict-based, not single instrument)
    ltp: Dict[str, float] = field(default_factory=dict)
    ohlc: Dict[str, Any] = field(default_factory=dict)
    
    # Account/Risk
    positions: List[Any] = field(default_factory=list)
    margins: Dict[str, float] = field(default_factory=dict)
    
    # Patch 3: Enriched Context
    regime_snapshot: Optional[str] = None  # String, not Dict
    event_snapshot: Optional[Dict[str, Any]] = None
    
    # Execution Stats
    universe_size: int = 0
    token_count: int = 0
```

## Key Differences

1. **Instrument Scope**: Current = single instrument, Proposed = multi-instrument (dict-based)
2. **Market Data Format**: Current = `Tick`/`Bar` objects, Proposed = dict-based `ltp`/`ohlc`
3. **Regime Format**: Current = `Dict[str, Any]`, Proposed = `str` (simpler)
4. **Portfolio State**: Current = individual fields, Proposed = `positions` list + `margins` dict
5. **No `timestamp`**: Proposed structure doesn't include timestamp
6. **No `instrument` field**: Proposed is instrument-agnostic

## Migration Strategy

### Option A: Hybrid Approach (Recommended)
Keep current structure but add compatibility layer:
- Add `ltp` and `ohlc` dicts alongside existing fields
- Keep `regime_snapshot` as Dict but add helper to extract string
- Maintain backward compatibility

### Option B: Full Migration
Refactor all strategies to use new structure:
- More work but cleaner long-term
- Requires updating all strategy implementations
- Better alignment with StatGeist patterns

### Option C: Dual Support
Support both structures during transition:
- Strategies can use either pattern
- Orchestrator provides both formats
- Gradual migration

## Recommendation

**Option A (Hybrid)** for now because:
1. We just implemented patches - don't break working code
2. Current strategies expect `instrument`, `latest_tick`, `bars_5s`
3. Can add new fields alongside existing ones
4. Migrate strategies gradually

## Implementation Plan

1. **Extend current StrategyContext** with new fields (additive)
2. **Orchestrator populates both formats** (dict + objects)
3. **Strategies can use either** (backward compatible)
4. **New strategies use dict-based format** (forward compatible)

