# Strangle Strategies - Configuration Complete

## ✅ Configuration Applied

### 1. **Added to LIVE Config** (`configs/kite_day1_live.yaml`)

**Strategies Added:**
- ✅ `expiry_short_strangle_v2` - Priority 2, enabled
- ✅ `intraday_short_strangle_v1` - Priority 3, enabled

**Configuration:**
```yaml
strategies:
  # ... existing strategies ...
  
  - name: expiry_short_strangle_v2
    enabled: true
    priority: 2
    params:
      pass_through: true  # Loads from configs/expiry_short_strangle_v2.yaml

  - name: intraday_short_strangle_v1
    enabled: true
    priority: 3
    params:
      pass_through: true  # Loads from configs/intraday_short_strangle_v1.yaml
```

### 2. **Updated H1 Overlay** (`configs/tail_short_vol.yaml`)

**Short Vol Strategies List Updated:**
- ✅ Added `expiry_short_strangle_v2`
- ✅ Added `intraday_short_strangle_v1`

**H1 will now:**
- Monitor both new strategies for short premium exposure
- Automatically deploy tail hedges (10-15% of premium collected)
- Adjust coverage based on R1 regime

---

## 🎯 Strategy Priority Order

1. **Priority 0:** RegimeVolEngine (R1) - Runs first to classify regime
2. **Priority 1:** OptionsRanker - Primary debit spread strategy
3. **Priority 2:** expiry_short_strangle_v2 - Weekly income engine
4. **Priority 3:** intraday_short_strangle_v1 - Precision scalper
5. **Priority 4:** GammaScalper (G1)
6. **Priority 5:** CalendarArb (T1)
7. **Priority 6:** DispersionArb (D1)
8. **Priority 3:** TailShortVolOverlay (H1) - Overlay, monitors all short vol

---

## 📊 Expected Behavior on Startup

### Startup Logs (Expected)

```
[INFO] Strategy Loaded: RegimeVolEngine
[INFO] Strategy Loaded: OptionsRanker
[INFO] Strategy Loaded: Expiry Short Strangle V2
[INFO] Strategy Loaded: Intraday Short Strangle V1
[INFO] Strategy Loaded: GammaScalper
[INFO] Strategy Loaded: CalendarArb
[INFO] Strategy Loaded: DispersionArb
[INFO] Strategy Loaded: TailShortVolOverlay
[INFO] Loaded 8 strategies
```

### During Trading (Expected Sequence)

**09:20 AM:**
- Intraday strangle starts evaluating
- Checks regime, intraday vol, events, portfolio heat
- If all pass → Signal generated → Short strangle opened

**10:15 AM:**
- Expiry strangle starts evaluating
- Checks regime, IV, realized vol, move/ATR, portfolio heat
- If all pass → Signal generated → Weekly strangle opened

**10:16 AM:**
- H1 overlay detects short premium from both strategies
- Automatically buys tail hedges (15% of total premium collected)

**15:15 PM:**
- Intraday strangle hard exit time → Force close all positions

---

## ✅ Verification Steps

### Step 1: Start API

```bash
export APP_MODE=LIVE
export APP_CONFIG=configs/kite_day1_live.yaml
python3 -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8000
```

### Step 2: Check Logs

**Look for:**
```
"Strategy Loaded: Expiry Short Strangle V2"
"Strategy Loaded: Intraday Short Strangle V1"
```

### Step 3: Check Metrics

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

### Step 4: Check Strategy Summary

```bash
curl http://localhost:8000/api/strategies/summary | jq '.strategies[] | select(.name | contains("strangle"))'
```

**Expected:**
- Both strategies listed
- `enabled: true`
- `total_signals_generated: 0` (initially)

---

## 🎯 Next Steps

1. ✅ **Configuration Complete** - Strategies added to config
2. ⏳ **Start API** - Run in PAPER mode first
3. ⏳ **Monitor Logs** - Verify strategies load correctly
4. ⏳ **Monitor Metrics** - Check filter rejections during trading hours
5. ⏳ **Promote to LIVE** - After validation in PAPER mode

---

**Status:** ✅ **Configuration Complete**

The strategies are now configured and ready to load on next API startup.

---

**Last Updated:** 2025-11-19  
**Status:** Ready for startup

