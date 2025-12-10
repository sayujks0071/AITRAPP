# Live Trading Debug & Fix Guide

## Problem
No trades have been generated in the last month despite the system running.

## Root Cause Analysis

After analyzing the codebase, here are the **most likely blocking conditions**:

### 1. ✅ DRY_RUN Mode (FIXED)
- **Status**: Fixed - Added explicit `dry_run: false` to config
- **Location**: `configs/kite_day1_live.yaml` → `execution.dry_run`
- **Impact**: If `dry_run: true`, signals are approved but NOT executed
- **Code**: `packages/core/orchestrator.py:1606`

### 2. ⚠️ System Paused State
- **Location**: `packages/core/orchestrator.py:1400`
- **Check**: `if self.is_paused: return`
- **How to verify**: 
  ```bash
  curl http://localhost:8000/control/state | jq '.is_paused'
  ```
- **Fix**: If paused, resume with:
  ```bash
  curl -X POST http://localhost:8000/resume
  ```

### 3. ⚠️ Empty Universe
- **Location**: `packages/core/orchestrator.py:1419`
- **Check**: `if universe_size == 0: return`
- **How to verify**: Check logs for `"Universe is empty in _scan_cycle"`
- **Fix**: Ensure instruments are synced:
  ```bash
  # Check universe sync
  grep "universe" logs/aitrapp.log | tail -20
  ```

### 4. ⚠️ No Signals Generated
- **Location**: `packages/core/orchestrator.py:1489`
- **Check**: `if not all_signals: return`
- **How to verify**: Check logs for `"Generated X signals"`
- **Possible causes**:
  - Strategies not enabled
  - Market data not streaming
  - Strategy validation failing
  - Entry window restrictions

### 5. ⚠️ Signals Rejected by Risk Manager
- **Location**: `packages/core/orchestrator.py:1588`
- **Check**: `if not risk_check.approved: continue`
- **How to verify**: Check logs for `"Signal rejected by risk manager"`
- **Common rejection reasons**:
  - Daily loss limit breached
  - Portfolio heat limit breached
  - Position size calculated as zero
  - Per-trade risk too high
  - Strategy loss limit exceeded

### 6. ⚠️ Kill Switch Active
- **Location**: `packages/core/execution/execution_engine.py:475`
- **Check**: `if self._kill_switch_check(): return BLOCKED`
- **How to verify**: Check logs for `"Order blocked: Kill switch active"`
- **Fix**: Resume trading if paused

### 7. ⚠️ Pre-Trade Safety Check Blocking
- **Location**: `packages/core/orchestrator.py:1530`
- **Check**: Self-healing diagnostics may block trading
- **How to verify**: Check logs for `"Trading blocked by self-healing diagnostics"`

## Diagnostic Commands

### 1. Check System State
```bash
curl http://localhost:8000/control/state | jq
```

Look for:
- `is_paused: false` (should be false)
- `is_market_open: true` (during market hours)
- `trades_today: 0` (if 0, no trades executed)

### 2. Check Logs for Signal Generation
```bash
# Check if signals are being generated
grep "Generated.*signals" logs/aitrapp.log | tail -20

# Check if signals are being rejected
grep "Signal rejected" logs/aitrapp.log | tail -20

# Check if scan cycles are running
grep "Running scan cycle" logs/aitrapp.log | tail -20

# Check for dry_run mode
grep "DRY_RUN" logs/aitrapp.log | tail -10

# Check for kill switch
grep "kill switch\|Kill switch\|KILL_SWITCH" logs/aitrapp.log | tail -10

# Check for empty universe
grep "Universe is empty" logs/aitrapp.log | tail -10

# Check for execution
grep "Executing signal" logs/aitrapp.log | tail -20
```

### 3. Run Diagnostic Script
```bash
python3 scripts/debug_live_trading.py
```

## Step-by-Step Fix Process

### Step 1: Verify Configuration
```bash
# Check if dry_run is explicitly false
grep "dry_run" configs/kite_day1_live.yaml

# Should show: dry_run: false
```

### Step 2: Check System State
```bash
# Get system state
curl http://localhost:8000/control/state | jq

# If paused, resume
curl -X POST http://localhost:8000/resume
```

### Step 3: Verify Orchestrator is Running
```bash
# Check if scan cycles are running
grep "Running scan cycle" logs/aitrapp.log | tail -5

# Should see recent timestamps
```

### Step 4: Check Signal Generation
```bash
# Check if strategies are generating signals
grep "Generated.*signals" logs/aitrapp.log | tail -10

# If no signals, check:
# 1. Are strategies enabled?
# 2. Is market data streaming?
# 3. Are entry windows correct?
```

### Step 5: Check Risk Manager Rejections
```bash
# Check rejection reasons
grep "Signal rejected" logs/aitrapp.log | tail -20

# Common issues:
# - "Daily loss limit breached"
# - "Portfolio heat limit breached"
# - "Position size calculated as zero"
```

### Step 6: Monitor Real-Time
```bash
# Watch logs in real-time
tail -f logs/aitrapp.log | jq

# Look for:
# - "Running scan cycle"
# - "Generated X signals"
# - "Signal rejected" (with reasons)
# - "Executing signal"
# - "DRY_RUN" (should NOT appear)
```

## Common Issues & Solutions

### Issue 1: No Signals Generated
**Symptoms**: Logs show scan cycles but no "Generated X signals"
**Causes**:
- Strategies not enabled
- Market data not streaming
- Entry window restrictions
- Strategy validation failing

**Fix**:
1. Check strategy config: `grep "enabled:" configs/kite_day1_live.yaml`
2. Check market data: `grep "Market data" logs/aitrapp.log`
3. Check entry window: Verify `entry.window_start` and `entry.window_end` in config

### Issue 2: Signals Rejected by Risk Manager
**Symptoms**: Logs show "Signal rejected" with reasons
**Causes**:
- Daily loss limit breached
- Portfolio heat limit too low
- Position size calculation issues

**Fix**:
1. Check risk config: `grep -A 5 "risk:" configs/kite_day1_live.yaml`
2. Adjust limits if too conservative
3. Check portfolio state: `curl http://localhost:8000/control/state | jq`

### Issue 3: System Paused
**Symptoms**: `is_paused: true` in system state
**Fix**:
```bash
curl -X POST http://localhost:8000/resume
```

### Issue 4: Empty Universe
**Symptoms**: Logs show "Universe is empty in _scan_cycle"
**Fix**:
1. Check instrument sync: `grep "sync" logs/aitrapp.log`
2. Verify universe config: `grep -A 10 "universe:" configs/kite_day1_live.yaml`
3. Restart system to trigger universe sync

## Verification Checklist

- [ ] `dry_run: false` in config (FIXED)
- [ ] System not paused (`is_paused: false`)
- [ ] Universe not empty (check logs)
- [ ] Signals being generated (check logs)
- [ ] Signals not all rejected (check logs)
- [ ] Kill switch not active (check logs)
- [ ] Scan cycles running (check logs)
- [ ] Market data streaming (check logs)
- [ ] Strategies enabled (check config)
- [ ] Entry window correct (check config)

## Next Steps

1. **Run diagnostic script**: `python3 scripts/debug_live_trading.py`
2. **Check system state**: `curl http://localhost:8000/control/state | jq`
3. **Monitor logs**: `tail -f logs/aitrapp.log | jq`
4. **Verify fixes**: Look for "Executing signal" in logs

## Files Modified

1. `configs/kite_day1_live.yaml` - Added explicit `dry_run: false`
2. `scripts/debug_live_trading.py` - Created diagnostic tool

## Additional Notes

- The orchestrator runs scan cycles every 5 seconds (configurable)
- Signals are ranked and only top opportunities are executed
- Risk manager validates all signals before execution
- Execution engine enforces rate limiting and kill switch checks
- All blocking conditions are logged for debugging

