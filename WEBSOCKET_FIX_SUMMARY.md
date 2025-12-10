# WebSocket 403 Error - Root Cause & Fix

## Problem Summary
- **Symptom**: WebSocket connection failing with 403 Forbidden error
- **Impact**: No market data = No trading possible
- **Duration**: 2+ hours of downtime

## Root Cause Analysis

### Initial Hypothesis
The 403 error suggested that WebSocket streaming was not enabled in the Kite Connect app settings.

### Actual Root Cause
After running diagnostic script (`scripts/check_kite_websocket.py`), we discovered:
1. ✅ **REST API**: Working correctly
2. ✅ **WebSocket**: Working correctly when tested directly
3. ❌ **Server MarketDataStream**: Not being started during application startup

### The Bug
In `apps/api/main.py` (line 624), the MarketDataStream was being **initialized** but never **started**:

```python
# Initialize market data stream
app_state.market_data_stream.initialize()  # ✅ Initialized
# ❌ Missing: app_state.market_data_stream.start()
```

The `start()` method was only called in the `/market-data/restart` endpoint, but not during initial application startup.

## Fix Applied

### Code Changes
1. **Enhanced error logging** in `packages/core/market_data.py`:
   - Added specific 403 error message with instructions to check Kite app settings

2. **Fixed startup sequence** in `apps/api/main.py`:
   - Added `app_state.market_data_stream.start()` after initialization
   - Added automatic subscription to universe tokens after connection is established
   - Added delayed subscription task to allow WebSocket connection to establish first

### New Code (lines 623-641)
```python
# Initialize and start market data stream
app_state.market_data_stream.initialize()
app_state.market_data_stream.start()

# Subscribe to universe tokens after a short delay to allow connection
async def subscribe_to_universe_delayed():
    await asyncio.sleep(3)  # Wait for WebSocket connection to establish
    if app_state.market_data_stream.is_connected:
        universe_tokens = app_state.instrument_manager.get_universe_tokens()
        if universe_tokens:
            # Subscribe to first 50 tokens (or all if less than 50)
            tokens_to_subscribe = universe_tokens[:50]
            app_state.market_data_stream.subscribe(tokens_to_subscribe)
            logger.info(f"Subscribed to {len(tokens_to_subscribe)} instruments for market data")
    else:
        logger.warning("Market data stream not connected, skipping subscription")

# Start subscription task
asyncio.create_task(subscribe_to_universe_delayed())
```

## Diagnostic Tools Created

### `scripts/check_kite_websocket.py`
A diagnostic script that:
- Tests REST API connection
- Tests WebSocket connection directly
- Provides clear error messages if 403 occurs
- Gives step-by-step instructions to enable WebSocket streaming in Kite app settings

**Usage:**
```bash
python3 scripts/check_kite_websocket.py
```

## Verification Steps

1. **Check server status:**
   ```bash
   curl http://localhost:8000/state | jq '.marketdata_connected, .websocket_connected'
   ```

2. **Check diagnostic script:**
   ```bash
   python3 scripts/check_kite_websocket.py
   ```

3. **Check server logs:**
   ```bash
   tail -f /tmp/uvicorn.log | grep -i "websocket\|market.*data"
   ```

## Expected Behavior After Fix

1. ✅ MarketDataStream starts automatically on server startup
2. ✅ WebSocket connection establishes within 3-5 seconds
3. ✅ Universe tokens are subscribed automatically after connection
4. ✅ Market data heartbeats update regularly (< 5 seconds)
5. ✅ Strategies can receive market data and generate signals

## Prevention

- The fix ensures MarketDataStream is always started during application startup
- Enhanced error logging will catch 403 errors early with clear instructions
- Diagnostic script can be run anytime to verify WebSocket connectivity

## Notes

- **Kite App Settings**: The diagnostic confirmed WebSocket streaming IS enabled for the app
- **Token Validity**: Token is valid for both REST and WebSocket (confirmed by diagnostic)
- **Connection Timing**: Added 3-second delay before subscription to allow connection to establish

