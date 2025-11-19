# Day-4 Root Cause Analysis
**Date:** 2025-11-19  
**Issue:** Zero setups evaluated, zero signals generated

---

## 🔴 ROOT CAUSE IDENTIFIED

### Primary Issue: Universe Contains Only Futures, Not Options

**Finding:**
- Universe tokens: `[9485826, 12683010]` (2 tokens)
- Both tokens are **NIFTY FUTURES** (FUT), not options
- **OptionsRanker requires NIFTY OPTIONS (CE/PE)** to evaluate debit spread setups
- Result: Strategies run but have no instruments to evaluate

**Evidence:**
```python
# Universe building only adds:
1. Spot index (EQ) - ✅ Added
2. Futures (FUT) - ✅ Added (2 tokens)
3. Options (CE/PE) - ❌ NOT ADDED
```

**Impact:**
- Scan cycles run every 5 seconds (517 ticks completed)
- Strategies are loaded and enabled
- But `_scan_cycle()` iterates over universe tokens (only 2 futures)
- OptionsRanker's `generate_signals()` never gets called with options
- Result: 0 setups evaluated, 0 signals generated

---

## 🔍 SECONDARY ISSUES

### 1. Strategy Summary Endpoint Missing `enabled` Field
- **Status:** ✅ FIXED
- **Issue:** `/api/strategies/summary` didn't include `enabled` status
- **Fix:** Added `enabled: getattr(strategy, 'enabled', True)` to response

### 2. Market Data Bars May Be Missing
- **Status:** ⚠️ NEEDS VERIFICATION
- **Issue:** Scan cycle checks `if not tick or not bars_5s: continue`
- **Impact:** Even if options were in universe, missing bars would skip strategy calls
- **Action:** Verify bars_5s are being built for subscribed instruments

### 3. Universe Building Logic Incomplete
- **Status:** ✅ FIXED
- **Issue:** `_get_index_instruments()` only added futures, not options
- **Fix:** Added options (CE/PE) expiring within 30 days to universe

---

## 📊 DIAGNOSTIC SUMMARY

### What Was Working:
- ✅ API running and healthy
- ✅ Market data WebSocket connected (2 subscriptions)
- ✅ Scan supervisor running (517 scan ticks)
- ✅ Leader lock acquired
- ✅ Strategies loaded and enabled
- ✅ Scan cycles executing every 5 seconds

### What Was Broken:
- ❌ Universe only contained futures (2 tokens)
- ❌ No options in universe → OptionsRanker has nothing to evaluate
- ❌ Strategy summary endpoint missing `enabled` field
- ❌ No logging when strategies skip due to missing instruments

---

## 🛠️ FIXES APPLIED

### Fix 1: Add Options to Universe
**File:** `packages/core/instruments.py`
**Change:** Modified `_get_index_instruments()` to include options (CE/PE) expiring within 30 days

```python
elif inst.is_option and inst.expiry:
    # Include options expiring within next 30 days (for OptionsRanker)
    if inst.expiry <= now + timedelta(days=30):
        tokens.add(token)
```

### Fix 2: Add `enabled` Field to Strategy Summary
**File:** `apps/api/routes/mcp_analyst.py`
**Change:** Added `enabled` field to strategy info response

```python
"enabled": getattr(strategy, 'enabled', True),  # Strategy enabled status
```

---

## 🎯 VERIFICATION STEPS

### Step 1: Verify Universe Includes Options
```bash
# After restart, check universe:
curl -s http://localhost:8000/api/strategies/summary | jq '.strategies[].enabled'
```

### Step 2: Check Universe Size
```python
# Should see > 100 tokens (futures + options)
universe_tokens = instrument_manager.get_universe_tokens()
print(f"Universe size: {len(universe_tokens)}")
```

### Step 3: Monitor Signal Generation
```bash
# During market hours, check:
bash scripts/query_signal_metrics.sh
# Should see setups being evaluated
```

### Step 4: Verify Market Data Bars
```python
# Check if bars_5s are available:
bars_5s = market_data_stream.get_bars(token, 5, n=100)
print(f"Bars available: {len(bars_5s) if bars_5s else 0}")
```

---

## 📝 RECOMMENDATIONS

### Immediate (Before Day-5):
1. ✅ **FIXED:** Add options to universe builder
2. ✅ **FIXED:** Add `enabled` field to strategy summary
3. ⚠️ **TODO:** Restart API to apply universe fix
4. ⚠️ **TODO:** Verify universe includes options after restart
5. ⚠️ **TODO:** Monitor signal generation during market hours

### Short-term (Days 5-7):
1. Add logging when strategies skip due to missing instruments
2. Add metrics for universe size and instrument types
3. Verify market data bars are being built for all subscribed instruments
4. Add alert if universe size drops below threshold

### Long-term:
1. Add universe validation at startup
2. Add health check for universe completeness
3. Add automatic universe refresh if instruments expire
4. Add universe size monitoring and alerts

---

## ✅ EXPECTED OUTCOME (Day-5)

After fixes:
- Universe should contain 100+ tokens (futures + options)
- OptionsRanker should evaluate setups during scan cycles
- Signal metrics should show setups evaluated > 0
- If market conditions are favorable, signals should be generated

---

**Report Generated:** 2025-11-19 18:56 IST  
**Status:** Root cause identified and fixed  
**Next Action:** Restart API and verify universe includes options

