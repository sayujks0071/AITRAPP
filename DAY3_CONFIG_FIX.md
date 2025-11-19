# Day-3 Configuration Mismatch - FIXED

## 🔴 Critical Issue Identified

**Problem**: System ran Day-3 with `APP_MODE=LIVE` but loaded default `configs/app.yaml` (crypto config) instead of `configs/kite_day1_live.yaml` (NSE config).

**Impact**: 
- Crypto strategies (ORB, TrendPullback) loaded instead of NSE strategies (OptionsRanker, expiry_short_strangle, H1)
- Zero trades executed (strategies incompatible with venue)
- Day-3 generated no usable data

## ✅ Fixes Implemented

### 1. Automatic Config Selection (packages/core/config.py)

**Added**:
- `APP_CONFIG` environment variable support
- Auto-selection logic: When `APP_MODE=LIVE`, automatically loads `configs/kite_day1_live.yaml` if it exists
- Fallback to `configs/kite_canary_live.yaml` if day1 doesn't exist
- Explicit `APP_CONFIG` takes precedence over auto-selection

**Code**:
```python
def _get_config_path() -> str:
    """Determine which config file to load"""
    # Explicit APP_CONFIG takes precedence
    if settings.app_config_path:
        return settings.app_config_path
    
    # Auto-select based on APP_MODE
    if settings.app_mode == AppMode.LIVE:
        nse_config = Path("configs/kite_day1_live.yaml")
        if nse_config.exists():
            return str(nse_config)
        canary_config = Path("configs/kite_canary_live.yaml")
        if canary_config.exists():
            return str(canary_config)
    
    # Default to app.yaml
    return "configs/app.yaml"
```

### 2. Startup Validation (apps/api/main.py)

**Added**: Critical validation that runs at startup for LIVE mode:
- Verifies venue is NSE (not BINANCE_SPOT or other crypto venues)
- Verifies required strategies are loaded (OptionsRanker minimum)
- **FAILS FAST** with clear error message if mismatch detected

**Code**:
```python
if settings.app_mode.value == "LIVE":
    venue_name = app_config.venue.get("name", "UNKNOWN")
    strategy_names = [s.name for s in app_config.get_enabled_strategies()]
    
    # Verify NSE venue
    if venue_name not in ["NSE", "NFO"]:
        raise ValueError(
            f"LIVE mode requires NSE venue, but loaded config has venue={venue_name}. "
            f"Config loaded from: {app_config.config_path}. "
            f"Set APP_CONFIG=configs/kite_day1_live.yaml to fix."
        )
    
    # Verify expected strategies
    expected_strategies = ["OptionsRanker"]
    missing = [s for s in expected_strategies if s not in strategy_names]
    if missing:
        raise ValueError(
            f"LIVE mode missing required strategies: {missing}. "
            f"Loaded strategies: {strategy_names}. "
            f"Config loaded from: {app_config.config_path}."
        )
```

## 🧪 Verification

**Test Result** (with APP_MODE=LIVE):
```
Config path: configs/kite_day1_live.yaml
Venue: NSE
Strategies: ['OptionsRanker', 'expiry_short_strangle', 'TailShortVolOverlay']
```

✅ **PASSED** - Correct config now loads automatically

## 📋 Day-4 Startup Checklist

### Before Market Open (08:55 IST)

1. **Set Environment Variables**:
   ```bash
   export APP_MODE=LIVE
   # APP_CONFIG is optional now (auto-detects), but explicit is safer:
   export APP_CONFIG=configs/kite_day1_live.yaml
   ```

2. **Start API**:
   ```bash
   python -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8000
   ```

3. **Verify Config Loaded Correctly** (within 30 seconds of startup):
   ```bash
   curl -s http://localhost:8000/state | jq '.mode, .strategies'
   ```
   
   **Expected Output**:
   ```json
   "LIVE"
   ["OptionsRanker", "expiry_short_strangle", "TailShortVolOverlay"]
   ```
   
   **If you see** `["ORB", "TrendPullback"]` → **STOP** and check config loading

4. **Check Startup Logs**:
   Look for:
   ```
   LIVE mode config validation PASSED
   venue=NSE
   strategies=['OptionsRanker', 'expiry_short_strangle', 'TailShortVolOverlay']
   config_path=configs/kite_day1_live.yaml
   ```

5. **Manual Kite Reconciliation** (CRITICAL):
   - [ ] Login to kite.zerodha.com
   - [ ] Verify 0 positions (all segments)
   - [ ] Verify 0 pending orders
   - [ ] Verify 0 AMO orders
   - [ ] Verify margin ≈ ₹1,000,000 available

## 🚨 What Happens Now

### If Config Mismatch Detected:
- **System will FAIL TO START** with clear error message
- **No silent failures** - you'll know immediately
- **Error message tells you exactly what to fix**

### If Config Correct:
- System starts normally
- Logs show validation passed
- Strategies load correctly
- Trading can proceed

## 📊 Additional Recommendations

### 1. Enable R1/E1 Engines
Add to `configs/kite_day1_live.yaml`:
```yaml
strategies:
  - name: RegimeVolEngine
    enabled: true
  - name: EventVolEngine
    enabled: true
```

### 2. Add Signal Generation Metrics
Monitor signal generation in real-time:
```bash
watch -n 5 'curl -s http://localhost:8000/metrics | grep signals_generated'
```

### 3. Fix MCP Broker Reconciliation
Fix import path in `mcp-adapters/trading_analyst_adapter.py`:
```python
# Change from:
from exchanges.kite_client import get_kite_client
# To:
from packages.exchanges.kite_client import get_kite_client
```

## ✅ Summary

**Status**: **FIXED**

- ✅ Config auto-selection implemented
- ✅ Startup validation added
- ✅ Fails fast with clear errors
- ✅ Verified working with test

**Next Steps**:
1. Use Day-4 startup checklist above
2. Monitor startup logs for validation message
3. Verify strategies loaded correctly
4. Proceed with Day-4 trading

**Risk Level**: **REDUCED** - System now prevents config mismatches at startup


