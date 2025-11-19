# Strategy Orchestrator Analysis Report

**Date:** 2025-11-19  
**Analyst:** AI Pair-Programmer  
**Scope:** Complete analysis of strategy wiring, orchestrator integration, and improvement recommendations

---

## 📊 Executive Summary

**Total Strategies:** 13 strategies identified  
**Orchestrator Pattern:** Sequential scan cycle with StrategyContext  
**Integration Status:** ✅ Functional but has optimization opportunities  
**Critical Issues:** 3 high-priority, 5 medium-priority improvements identified

---

## 1. Orchestrator Architecture

### 1.1 Scan Cycle Flow

```
_scan_supervisor() [runs every 5 seconds]
    ↓
_scan_cycle() [throttled to scan_interval_seconds]
    ↓
For each strategy in self.strategies:
    ↓
    For each token in universe[:20]:  # ⚠️ LIMITED TO 20 TOKENS
        ↓
        Build StrategyContext (tick, bars, portfolio state)
        ↓
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

### 1.2 Key Components

**TradingOrchestrator** (`packages/core/orchestrator.py`)
- **Scan Interval:** 5 seconds (hardcoded)
- **Universe Limit:** 20 tokens per strategy (performance limit)
- **Signal Limit:** Top 3 opportunities per cycle
- **Strategy Execution:** Sequential (not parallelized)

**StrategyContext** (`packages/core/strategies/base.py`)
- Provides: timestamp, instrument, tick, bars, portfolio state
- Missing: regime context, event context, IV percentile (partially available)

---

## 2. Strategy Inventory

### 2.1 All Strategies (13 Total)

| Strategy | Type | Priority | Status | Config File |
|----------|------|----------|--------|-------------|
| **RegimeVolEngine** (R1) | Meta | 0 | ✅ Enabled | `regime_vol_engine.yaml` |
| **OptionsRanker** | Primary | 1 | ✅ Enabled | Inline in `kite_day1_live.yaml` |
| **expiry_short_strangle** | Secondary | 2 | ✅ Enabled | Inline in `kite_day1_live.yaml` |
| **expiry_short_strangle_v2** | Premium | 2 | ✅ Enabled | `expiry_short_strangle_v2.yaml` |
| **intraday_short_strangle_v1** | Premium | 3 | ✅ Enabled | `intraday_short_strangle_v1.yaml` |
| **TailShortVolOverlay** (H1) | Overlay | 3 | ✅ Enabled | `tail_short_vol.yaml` |
| **trend_credit_spread_v1** | Premium | 4 | ✅ Enabled | `trend_credit_spread_v1.yaml` |
| **GammaScalper** (G1) | Premium | 4 | ✅ Enabled | `gamma_scalper.yaml` |
| **CalendarArb** (T1) | Premium | 5 | ✅ Enabled | `calendar_arb.yaml` |
| **DispersionArb** (D1) | Premium | 6 | ✅ Enabled | `dispersion_arb.yaml` |
| **ORB** | Legacy | N/A | ❌ Disabled | Crypto config |
| **TrendPullback** | Legacy | N/A | ❌ Disabled | Crypto config |
| **IronCondor** | Legacy | N/A | ❌ Disabled | Not in LIVE config |

### 2.2 Strategy Categories

**Meta-Strategies (Run First):**
- **R1: RegimeVolEngine** - Classifies market regime (LOW_MEAN_REVERT, MEDIUM_TREND, HIGH_EVENT, CHAOTIC)
- **E1: EventVolEngine** - Detects major events (RBI policy, US CPI, earnings)

**Primary Strategies:**
- **OptionsRanker** - Debit spreads on NIFTY options (main workhorse)

**Secondary Strategies:**
- **expiry_short_strangle** - Weekly short strangle (V1)
- **expiry_short_strangle_v2** - Regime-aware weekly short strangle (V2)

**Premium Strategies:**
- **intraday_short_strangle_v1** - Precision intraday scalper
- **trend_credit_spread_v1** - ADX-filtered directional credit spreads
- **G1: GammaScalper** - Long gamma with futures hedge
- **T1: CalendarArb** - Calendar arbitrage
- **D1: DispersionArb** - Dispersion arbitrage

**Overlay Strategies:**
- **H1: TailShortVolOverlay** - Auto-hedge for short premium exposure

---

## 3. Strategy Wiring Analysis

### 3.1 Initialization Pattern (`apps/api/main.py`)

**Current Pattern:**
```python
for strategy_config in app_config.get_enabled_strategies():
    strategy = None
    if strategy_config.name == "OptionsRanker":
        strategy = OptionsRankerStrategy(...)
    elif strategy_config.name == "RegimeVolEngine":
        # Load from separate YAML
        strategy = RegimeVolEngine(...)
    elif strategy_config.name == "expiry_short_strangle_v2":
        # Load from separate YAML
        strategy = ExpiryShortStrangleV2(...)
    # ... 10+ more elif blocks
    
    if strategy:
        app_state.strategies[name] = strategy
        strategy_registry[name] = strategy
        strategy_list.append(strategy)
```

**Issues:**
1. ❌ **Massive if/elif chain** (13+ branches) - hard to maintain
2. ❌ **Inconsistent dependency injection** - some get `regime_engine`, some don't
3. ❌ **No factory pattern** - manual instantiation for each strategy
4. ❌ **Config loading duplication** - YAML loading repeated for each strategy
5. ❌ **No strategy registry lookup** - can't dynamically discover strategies

### 3.2 Execution Pattern (`packages/core/orchestrator.py`)

**Current Pattern:**
```python
async def _scan_cycle(self):
    all_signals = []
    
    for strategy in self.strategies:
        if not strategy.enabled:
            continue
        
        # ⚠️ LIMITED TO 20 TOKENS
        universe_tokens = self.instrument_manager.get_universe_tokens()
        
        for token in universe_tokens[:20]:  # Performance limit
            instrument = self.instrument_manager.get_instrument(token)
            tick = self.market_data_stream.get_latest_tick(token)
            bars_1s = self.market_data_stream.get_bars(token, 1, n=60)
            bars_5s = self.market_data_stream.get_bars(token, 5, n=100)
            
            context = StrategyContext(
                timestamp=current_time,
                instrument=instrument,
                latest_tick=tick,
                bars_1s=bars_1s,
                bars_5s=bars_5s,
                net_liquid=self._get_net_liquid(),
                available_margin=self._get_available_margin(),
                open_positions=len([p for p in self.positions if p.is_open])
            )
            
            signals = strategy.generate_signals(context)
            all_signals.extend(signals)
```

**Issues:**
1. ❌ **Sequential execution** - strategies run one after another (not parallelized)
2. ❌ **Token limit (20)** - only evaluates first 20 tokens (universe may have 400+)
3. ❌ **No priority ordering** - strategies run in list order, not priority order
4. ❌ **Context missing regime/event** - StrategyContext doesn't include R1/E1 context
5. ❌ **No strategy-specific filtering** - all strategies see all tokens (inefficient)

---

## 4. Strategy Allocator Integration

### 4.1 Current Integration

**Initialization:**
- StrategyAllocator is initialized in `apps/api/main.py`
- Passed to orchestrator: `strategy_allocator=app_state.strategy_allocator`
- Runs allocation cycle at startup (once)

**Execution:**
- Called once at orchestrator startup
- Not called periodically during trading hours
- Not triggered on regime changes
- Not triggered on event detection

**Issues:**
1. ❌ **Runs only once** - allocation doesn't adapt during the day
2. ❌ **No periodic refresh** - weights don't update based on intraday performance
3. ❌ **No regime change trigger** - doesn't reallocate when R1 regime switches
4. ❌ **No event trigger** - doesn't reallocate when E1 detects events

### 4.2 Strategy Allocator Configuration

**Current Weights** (`configs/strategy_allocator.yaml`):
- OptionsRanker: 45%
- expiry_short_strangle: 10%
- gamma_scalper: 15%
- calendar_arb: 15%
- dispersion_arb: 10%
- Others: 0%

**Issues:**
1. ⚠️ **Missing new strategies** - `expiry_short_strangle_v2`, `intraday_short_strangle_v1`, `trend_credit_spread_v1` not in allocator config
2. ⚠️ **No overlay strategy** - H1 (TailShortVolOverlay) not in allocator (may be intentional)

---

## 5. Critical Issues

### 🔴 High Priority

#### Issue 1: Token Limit (20 tokens max)
**Location:** `packages/core/orchestrator.py:692`

**Problem:**
```python
for token in universe_tokens[:20]:  # Limit for performance
```

**Impact:**
- Universe has 400+ tokens (NIFTY spot, futures, options)
- Only first 20 tokens are evaluated
- Strategies may miss opportunities on tokens 21-400
- OptionsRanker needs options, but may only see futures/spot

**Recommendation:**
- Strategy-specific token filtering (each strategy declares which tokens it needs)
- Or: Increase limit to 50-100 tokens
- Or: Parallelize strategy execution to handle more tokens

#### Issue 2: No Priority Ordering
**Location:** `packages/core/orchestrator.py:684`

**Problem:**
- Strategies run in list order (from `strategy_list`)
- Priority field in config is ignored during execution
- R1 (priority 0) may run after other strategies

**Impact:**
- R1 regime classification may not be available when other strategies run
- Strategies that depend on R1 may get stale/null regime

**Recommendation:**
```python
# Sort strategies by priority before execution
sorted_strategies = sorted(
    self.strategies,
    key=lambda s: getattr(s, 'priority', 999)
)
for strategy in sorted_strategies:
    # ...
```

#### Issue 3: StrategyContext Missing Regime/Event Context
**Location:** `packages/core/strategies/base.py:11`

**Problem:**
- StrategyContext doesn't include `current_regime` (from R1)
- StrategyContext doesn't include `event_context` (from E1)
- Strategies that need regime/event must fetch it themselves

**Impact:**
- `expiry_short_strangle_v2` must call `regime_engine.get_current_regime()` manually
- `intraday_short_strangle_v1` must call `event_engine.has_major_event_today()` manually
- Inefficient and error-prone

**Recommendation:**
```python
@dataclass
class StrategyContext:
    # ... existing fields ...
    
    # Add regime/event context
    current_regime: Optional[str] = None  # From R1
    event_context: Optional[Any] = None  # From E1
```

### ⚠️ Medium Priority

#### Issue 4: Sequential Strategy Execution
**Problem:**
- Strategies run sequentially (one after another)
- No parallelization

**Impact:**
- Slow scan cycle (13 strategies × 20 tokens = 260 iterations)
- Each strategy waits for previous to complete

**Recommendation:**
```python
# Parallelize strategy execution
import asyncio

async def _scan_cycle(self):
    tasks = []
    for strategy in self.strategies:
        task = asyncio.create_task(
            self._generate_signals_for_strategy(strategy)
        )
        tasks.append(task)
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    all_signals = [s for r in results for s in (r if not isinstance(r, Exception) else [])]
```

#### Issue 5: Massive if/elif Chain in main.py
**Problem:**
- 13+ if/elif blocks for strategy instantiation
- Hard to maintain, easy to miss new strategies

**Recommendation:**
```python
# Strategy Factory Pattern
class StrategyFactory:
    _registry = {}
    
    @classmethod
    def register(cls, name: str, strategy_class: Type[Strategy]):
        cls._registry[name] = strategy_class
    
    @classmethod
    def create(cls, name: str, config: Dict, **deps) -> Strategy:
        strategy_class = cls._registry.get(name)
        if not strategy_class:
            raise ValueError(f"Unknown strategy: {name}")
        return strategy_class(name, config, **deps)

# Register all strategies
StrategyFactory.register("OptionsRanker", OptionsRankerStrategy)
StrategyFactory.register("RegimeVolEngine", RegimeVolEngine)
# ... etc

# Use factory
strategy = StrategyFactory.create(
    strategy_config.name,
    strategy_config.params,
    instrument_manager=app_state.instrument_manager,
    # ... other deps
)
```

#### Issue 6: Strategy Allocator Not Periodic
**Problem:**
- Allocator runs only once at startup
- Doesn't adapt to intraday performance or regime changes

**Recommendation:**
```python
# In orchestrator, add periodic allocation refresh
async def _scan_supervisor(self):
    last_allocation_time = None
    allocation_interval = 3600  # 1 hour
    
    while not self._stop.is_set():
        now = datetime.now()
        
        # Refresh allocation every hour
        if (not last_allocation_time or 
            (now - last_allocation_time).total_seconds() >= allocation_interval):
            if self.strategy_allocator:
                current_regime = self._get_current_regime()
                self.strategy_allocator.run_allocation_cycle(
                    current_regime=current_regime
                )
            last_allocation_time = now
        
        await self._scan_cycle()
        await asyncio.sleep(self.scan_interval_seconds)
```

#### Issue 7: Missing Strategies in Allocator Config
**Problem:**
- `expiry_short_strangle_v2` not in `strategy_allocator.yaml`
- `intraday_short_strangle_v1` not in `strategy_allocator.yaml`
- `trend_credit_spread_v1` not in `strategy_allocator.yaml`

**Recommendation:**
Add to `configs/strategy_allocator.yaml`:
```yaml
strategies:
  # ... existing ...
  
  - name: "expiry_short_strangle_v2"
    base_weight: 0.10
    role: "income_short_vol"
  
  - name: "intraday_short_strangle_v1"
    base_weight: 0.05
    role: "intraday_short_vol"
  
  - name: "trend_credit_spread_v1"
    base_weight: 0.05
    role: "directional_income"
```

#### Issue 8: No Strategy-Specific Token Filtering
**Problem:**
- All strategies see all tokens
- OptionsRanker doesn't need futures, but gets them anyway
- GammaScalper may only need specific underlyings

**Recommendation:**
```python
# Add to Strategy base class
class Strategy(ABC):
    def get_required_tokens(self) -> Optional[List[int]]:
        """
        Return list of tokens this strategy needs, or None for all.
        """
        return None  # Default: all tokens

# In orchestrator
for strategy in self.strategies:
    required_tokens = strategy.get_required_tokens()
    tokens_to_evaluate = required_tokens or universe_tokens[:20]
    
    for token in tokens_to_evaluate:
        # ...
```

---

## 6. Strategy-Specific Analysis

### 6.1 RegimeVolEngine (R1)

**Wiring:**
- ✅ Loaded first (priority 0)
- ✅ Passed `strategy_registry` for coordination
- ✅ Runs before other strategies

**Issues:**
- ⚠️ Regime not automatically included in StrategyContext
- ⚠️ Other strategies must manually fetch regime

**Recommendation:**
- Add regime to StrategyContext automatically after R1 runs

### 6.2 OptionsRanker

**Wiring:**
- ✅ Primary strategy (priority 1)
- ✅ Inline config (not separate YAML)
- ✅ Gets instrument_manager, risk_engine

**Issues:**
- ⚠️ May not see options if token limit (20) only includes futures/spot
- ⚠️ No explicit dependency on R1 (but may benefit from regime)

**Recommendation:**
- Ensure options tokens are in first 20 tokens
- Or: Add strategy-specific token filtering

### 6.3 Premium Strategies (V2, Intraday, Trend)

**Wiring:**
- ✅ Load from separate YAML files
- ✅ Get `regime_engine` dependency (V2, Intraday)
- ✅ Get `event_engine` dependency (Intraday)
- ✅ Get `kite_client` dependency (Trend)

**Issues:**
- ⚠️ Not in StrategyAllocator config
- ⚠️ May not get regime/event in StrategyContext (must fetch manually)

**Recommendation:**
- Add to StrategyAllocator config
- Include regime/event in StrategyContext

### 6.4 Overlay Strategy (H1)

**Wiring:**
- ✅ Gets `position_store` dependency
- ✅ Monitors short vol strategies
- ✅ Priority 3 (runs after income strategies)

**Issues:**
- ⚠️ Not in StrategyAllocator (may be intentional - overlay, not alpha)
- ⚠️ Must manually check position_store for short vol exposure

**Recommendation:**
- Consider adding to StrategyAllocator with 0% weight (overlay only)
- Or: Keep out of allocator (overlay doesn't need capital allocation)

---

## 7. Performance Analysis

### 7.1 Scan Cycle Timing

**Current:**
- Scan interval: 5 seconds
- Strategies: 13
- Tokens per strategy: 20
- Total iterations: 13 × 20 = 260 per cycle

**Estimated Time:**
- Per strategy call: ~10-50ms (depends on complexity)
- Total per cycle: 260 × 25ms = 6.5 seconds
- **Problem:** Cycle may take longer than interval!

**Recommendation:**
- Parallelize strategy execution
- Reduce token limit or add strategy-specific filtering
- Increase scan interval to 10 seconds if needed

### 7.2 Memory Usage

**Current:**
- Each strategy holds state (positions, signals, etc.)
- StrategyContext created 260 times per cycle
- Market data cached in MarketDataStream

**Recommendation:**
- Reuse StrategyContext objects where possible
- Clear strategy state periodically
- Monitor memory usage with metrics

---

## 8. Improvement Recommendations

### 8.1 Immediate (High Priority)

1. **Fix Token Limit**
   - Increase to 50-100 tokens OR
   - Add strategy-specific token filtering

2. **Add Priority Ordering**
   - Sort strategies by priority before execution
   - Ensure R1 runs first

3. **Enhance StrategyContext**
   - Add `current_regime` field
   - Add `event_context` field
   - Populate from R1/E1 automatically

### 8.2 Short Term (Medium Priority)

4. **Parallelize Strategy Execution**
   - Use `asyncio.gather()` for concurrent execution
   - Monitor performance improvement

5. **Strategy Factory Pattern**
   - Replace if/elif chain with factory
   - Auto-register strategies from `__init__.py`

6. **Periodic Allocation Refresh**
   - Run allocator every hour
   - Trigger on regime changes
   - Trigger on event detection

7. **Add Missing Strategies to Allocator**
   - Add V2, Intraday, Trend to `strategy_allocator.yaml`
   - Set appropriate base weights

### 8.3 Long Term (Low Priority)

8. **Strategy-Specific Token Filtering**
   - Each strategy declares required tokens
   - Orchestrator filters tokens per strategy

9. **Strategy Dependency Graph**
   - Explicit dependency declaration
   - Automatic execution ordering

10. **Strategy Health Monitoring**
    - Track strategy execution time
    - Alert on slow/failing strategies
    - Circuit breaker for failing strategies

---

## 9. Code Quality Issues

### 9.1 Duplication

**Config Loading:**
- YAML loading code repeated 10+ times
- Each strategy has same pattern

**Recommendation:**
```python
def load_strategy_config(name: str, config_file: str) -> Dict:
    """Centralized config loading"""
    config_path = Path(f"configs/{config_file}")
    if config_path.exists():
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
            return config.get(name, {})
    return {}
```

### 9.2 Error Handling

**Current:**
```python
try:
    signals = strategy.generate_signals(context)
    all_signals.extend(signals)
except Exception as e:
    logger.error(f"Strategy {strategy.name} failed", error=str(e))
```

**Issues:**
- One strategy failure doesn't stop others (good)
- But: No retry, no circuit breaker, no metrics

**Recommendation:**
- Add strategy failure metrics
- Circuit breaker after N consecutive failures
- Retry with exponential backoff

### 9.3 Testing

**Current:**
- Individual strategy test scripts exist
- No integration tests for orchestrator
- No tests for strategy coordination

**Recommendation:**
- Add orchestrator integration tests
- Test strategy priority ordering
- Test StrategyContext population
- Test allocator integration

---

## 10. Summary & Action Items

### ✅ What's Working Well

1. ✅ Strategy base class is clean and extensible
2. ✅ StrategyContext provides good abstraction
3. ✅ Separate YAML configs for complex strategies
4. ✅ StrategyAllocator exists and works (just needs periodic refresh)
5. ✅ Error handling prevents one strategy from crashing others

### 🔴 Critical Fixes Needed

1. **Token Limit (20)** - Strategies may miss opportunities
2. **Priority Ordering** - R1 may not run first
3. **StrategyContext Enhancement** - Missing regime/event context

### ⚠️ Important Improvements

4. **Parallelization** - Speed up scan cycle
5. **Factory Pattern** - Reduce code duplication
6. **Periodic Allocation** - Adapt to intraday changes
7. **Missing Allocator Entries** - Add new strategies

### 📊 Metrics to Add

- `orchestrator_scan_cycle_duration_seconds` - Track cycle time
- `orchestrator_strategy_execution_time_seconds{strategy}` - Per-strategy timing
- `orchestrator_tokens_evaluated_total` - Track token coverage
- `orchestrator_strategy_failures_total{strategy}` - Track failures

---

## 11. Implementation Priority

### Phase 1 (This Week)
1. Fix token limit (increase to 50 or add filtering)
2. Add priority ordering
3. Enhance StrategyContext with regime/event

### Phase 2 (Next Week)
4. Parallelize strategy execution
5. Add missing strategies to allocator
6. Implement periodic allocation refresh

### Phase 3 (Next Month)
7. Strategy factory pattern
8. Strategy-specific token filtering
9. Enhanced error handling and circuit breakers

---

**Report Generated:** 2025-11-19  
**Next Review:** After Phase 1 implementation

