# Strangle Strategies Integration Summary

## ✅ What Was Done

### 1. **Applied Retries to Historical Data Fetching** (`packages/core/instruments.py`)

**Critical Fix:** Added retry decorators to data fetching operations that are the "oxygen" of delta-based strategies.

**Methods Enhanced:**
- ✅ `_fetch_instruments_with_retry()` - Fetches instrument list with retries
- ✅ `_fetch_quote_with_retry()` - Fetches quotes (spot prices) with retries

**Why This Matters:**
- Delta-based strike selection requires accurate spot prices
- If quote fetch fails at 09:19:59, strategy is blind at critical entry moment
- Retries ensure transient network failures don't block strategy execution

**Implementation:**
```python
@retry_api_call(retries=3, delay=1.0, exceptions=(NetworkException,))
def _fetch_instruments_with_retry(self, exchange: str) -> List[Dict]:
    """Fetch instruments with retry on network errors"""
    return self.kite.instruments(exchange)

@retry_api_call(retries=3, delay=1.0, exceptions=(NetworkException,))
def _fetch_quote_with_retry(self, instrument_key: str) -> Dict:
    """Fetch quote with retry on network errors"""
    return self.kite.quote(instrument_key)
```

### 2. **Wired Both Strategies into Main API** (`apps/api/main.py`)

**Strategies Integrated:**
- ✅ `expiry_short_strangle_v2` - Weekly income engine
- ✅ `intraday_short_strangle_v1` - Precision scalper

**Integration Pattern:**
- Loads config from separate YAML files (`configs/expiry_short_strangle_v2.yaml`, `configs/intraday_short_strangle_v1.yaml`)
- Passes all required dependencies (instrument_manager, risk_engine, regime_engine, event_engine)
- Registers in strategy registry for R1 meta-strategy coordination
- Logs strategy loading for verification

**Code Added:**
```python
elif strategy_config.name == "expiry_short_strangle_v2":
    # Load from configs/expiry_short_strangle_v2.yaml
    strategy = ExpiryShortStrangleV2(...)
    logger.info("Strategy Loaded: Expiry Short Strangle V2")

elif strategy_config.name == "intraday_short_strangle_v1":
    # Load from configs/intraday_short_strangle_v1.yaml
    strategy = IntradayShortStrangleV1(...)
    logger.info("Strategy Loaded: Intraday Short Strangle V1")
```

### 3. **Created Test Scenario Script** (`scripts/test_strangle_strategies.py`)

**Purpose:** Test strategies without waiting for market open.

**Test Cases:**
1. ✅ Good conditions (should generate signal)
2. ✅ Wrong regime (should reject)
3. ✅ Wrong time (should reject)
4. ✅ IV out of range (should reject)
5. ✅ Hard exit time (should generate exit signals)

**Usage:**
```bash
python3 scripts/test_strangle_strategies.py
```

---

## 🎯 Verification Steps

### Step 1: Dry Run (Paper Mode)

1. **Set strategies to PAPER mode:**
   ```yaml
   # configs/expiry_short_strangle_v2.yaml
   mode: PAPER
   
   # configs/intraday_short_strangle_v1.yaml
   mode: PAPER
   ```

2. **Add to LIVE config:**
   ```yaml
   # configs/kite_day1_live.yaml
   strategies:
     - name: expiry_short_strangle_v2
       enabled: true
       priority: 2
       params:
         pass_through: true
     
     - name: intraday_short_strangle_v1
       enabled: true
       priority: 3
       params:
         pass_through: true
   ```

3. **Start API:**
   ```bash
   export APP_MODE=LIVE
   export APP_CONFIG=configs/kite_day1_live.yaml
   python3 -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8000
   ```

### Step 2: Check Logs

**Look for strategy loading messages:**
```
"Strategy Loaded: Expiry Short Strangle V2"
"Strategy Loaded: Intraday Short Strangle V1"
```

**Check for retry logs (if data fetch fails):**
```
"API call failed, retrying" function=_fetch_quote_with_retry
"API call succeeded after retry"
```

### Step 3: Verify Data Fetching

**Check that historical data fetching works:**
- Monitor logs during instrument sync
- Check for retry attempts (should be rare)
- Verify spot prices are fetched correctly

### Step 4: Run Test Script

```bash
python3 scripts/test_strangle_strategies.py
```

**Expected Output:**
```
TEST: Expiry Short Strangle V2
[TEST 1] Good conditions → ✅ PASS: Signal generated
[TEST 2] Wrong regime → ✅ PASS: Correctly rejected
[TEST 3] Wrong time → ✅ PASS: Correctly rejected
[TEST 4] IV out of range → ✅ PASS: Correctly rejected

TEST: Intraday Short Strangle V1
[TEST 1] Good conditions → ✅ PASS: Signal generated
[TEST 2] Wrong time → ✅ PASS: Correctly rejected
[TEST 3] Hard exit time → ✅ PASS: Hard exit detected
[TEST 4] Wrong regime → ✅ PASS: Correctly rejected
```

### Step 5: Monitor Metrics

**Check Prometheus metrics:**
```bash
curl http://localhost:8000/metrics | grep strangle
```

**Expected Metrics:**
- `expiry_strangle_v2_setups_evaluated_total`
- `expiry_strangle_v2_filter_rejections_total`
- `expiry_strangle_v2_signals_approved_total`
- `intraday_strangle_v1_setups_evaluated_total`
- `intraday_strangle_v1_filter_rejections_total`
- `intraday_strangle_v1_signals_approved_total`

---

## 🔧 Files Modified

1. ✅ `packages/core/instruments.py`
   - Added retry decorators to `_fetch_instruments_with_retry()`
   - Added retry decorators to `_fetch_quote_with_retry()`
   - Updated `sync_instruments()` to use retry wrapper
   - Updated `_get_index_instruments()` to use retry wrapper

2. ✅ `apps/api/main.py`
   - Added imports for `ExpiryShortStrangleV2` and `IntradayShortStrangleV1`
   - Added strategy instantiation blocks for both strategies
   - Added config loading from YAML files
   - Added logging for strategy loading

3. ✅ `scripts/test_strangle_strategies.py` (new)
   - Mock data injection
   - Filter logic testing
   - Signal generation verification
   - Error-proofing validation

---

## 📊 Expected Behavior

### On Startup

```
[INFO] Strategy Loaded: Expiry Short Strangle V2
[INFO] Strategy Loaded: Intraday Short Strangle V1
[INFO] Universe: 400 instruments
[INFO] Trading Orchestrator started
```

### During Trading (Good Day)

```
09:20 AM: Intraday strangle starts evaluating
09:21 AM: All filters pass → Signal generated
09:21 AM: Short strangle opened (CE + PE, delta ~0.25 each)
10:15 AM: Expiry strangle starts evaluating
10:16 AM: All filters pass → Signal generated
10:16 AM: Weekly strangle opened (CE + PE, delta ~0.20 each)
```

### During Trading (Filtered Day)

```
09:20 AM: Intraday strangle starts evaluating
09:21 AM: Filter rejection: "regime_not_allowed" (regime=MEDIUM_TREND)
09:22 AM: Filter rejection: "intraday_vol_too_high" (vol=0.8%, max=0.6%)
10:15 AM: Expiry strangle starts evaluating
10:16 AM: Filter rejection: "iv_percentile_out_of_range" (ivp=35, min=40)
```

**Metrics will show filter rejections, helping you understand why signals aren't generated.**

---

## ✅ Summary

**Status:** ✅ **Integration Complete**

- ✅ Retries applied to historical data fetching
- ✅ Both strategies wired into main.py
- ✅ Test script created for verification
- ✅ Ready for paper mode testing

**Next Steps:**
1. Run test script to verify logic
2. Start API in PAPER mode
3. Monitor logs and metrics
4. Promote to tiny live size after validation

---

**Last Updated:** 2025-11-19  
**Integration Time:** ~20 minutes  
**Status:** Ready for testing

