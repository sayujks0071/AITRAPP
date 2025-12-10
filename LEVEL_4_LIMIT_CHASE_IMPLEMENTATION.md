# Level 4: Limit Chase Execution Engine - Implementation Summary

## Overview

The **Limit Chase Execution Engine** is a Level 4 upgrade that provides **Execution Alpha** by intelligently managing LIMIT orders to capture spread instead of paying it. This upgrade moves beyond static MARKET/LIMIT orders to dynamic price chasing that minimizes slippage.

## Key Features

### 1. Intelligent Price Chasing
- Places LIMIT orders at **Best Bid** (for BUY) or **Best Ask** (for SELL)
- If not filled within 500ms, cancels and modifies to new Best Bid/Ask + 1 tick
- Repeats until filled or max slippage exceeded

### 2. Slippage Protection
- Maximum slippage: **5 basis points (0.05%)** (configurable)
- Automatically cancels if price moves beyond threshold
- Falls back to standard execution if limit chase fails

### 3. Async-First Architecture
- Fully async implementation compatible with AITRAPP's async core
- Non-blocking order status checks
- Efficient price chasing loop

## Implementation Details

### Files Created/Modified

1. **`packages/core/execution/limit_chaser.py`** (NEW)
   - `LimitChaser` class: Core limit chase algorithm
   - `LimitChaseResult` dataclass: Execution result tracking
   - Methods:
     - `execute_limit_chase()`: Main execution method
     - `_get_best_limit_price()`: Fetches Best Bid/Ask from order book
     - `_place_limit_order()`: Places LIMIT order
     - `_modify_order()`: Modifies order price
     - `_check_order_status()`: Checks fill status
     - `_calculate_slippage()`: Computes slippage in basis points

2. **`packages/core/execution.py`** (MODIFIED)
   - Added `LimitChaser` initialization in `__init__`
   - Added `_place_entry_with_limit_chase()` method
   - Modified `_place_entry_order()` to use limit chase if enabled
   - Graceful fallback to standard execution on failure

3. **`packages/core/config.py`** (MODIFIED)
   - Added limit chase config fields to `ExecutionConfig`:
     - `use_limit_chase`: Enable/disable limit chase
     - `limit_chase_max_slippage_bps`: Max slippage threshold
     - `limit_chase_timeout_ms`: Time to wait before chasing
     - `limit_chase_max_chases`: Max number of price chases
     - `tick_size`: Minimum price increment

4. **`configs/kite_day1_live.yaml`** (MODIFIED)
   - Added limit chase configuration section:
     ```yaml
     use_limit_chase: true
     limit_chase_max_slippage_bps: 5.0
     limit_chase_timeout_ms: 500
     limit_chase_max_chases: 10
     tick_size: 0.05
     ```

## Algorithm Flow

```
1. Get initial LTP for slippage calculation
2. Get Best Bid (BUY) or Best Ask (SELL) for LIMIT price
3. Place LIMIT order at Best Bid/Ask
4. Loop:
   a. Wait 500ms
   b. Check if filled → SUCCESS
   c. Get new Best Bid/Ask
   d. Check slippage → Cancel if exceeded
   e. If price changed → Modify order
   f. Repeat until filled or max_chases reached
5. Return result (success/failure with details)
```

## Benefits

### Execution Alpha
- **Captures spread** instead of paying it
- Over 1,000 trades, this often exceeds strategy alpha
- Particularly effective in high volatility (exactly when you want to enter)

### Risk Management
- Hard slippage protection (5 bps default)
- Automatic cancellation if market moves too far
- Graceful fallback to standard execution

### Compatibility
- Works with existing `ExecutionEngine` architecture
- No breaking changes to existing strategies
- Can be enabled/disabled via config

## Configuration

### Enable Limit Chase
```yaml
execution:
  use_limit_chase: true              # Enable intelligent limit order chasing
  limit_chase_max_slippage_bps: 5.0  # Max 5 bps slippage (0.05%)
  limit_chase_timeout_ms: 500        # Wait 500ms before chasing price
  limit_chase_max_chases: 10          # Max 10 price chases before giving up
  tick_size: 0.05                    # NIFTY options tick size
```

### Disable Limit Chase
```yaml
execution:
  use_limit_chase: false  # Falls back to standard LIMIT/MARKET orders
```

## Usage

The limit chase is automatically used for **entry orders** when:
1. `use_limit_chase: true` in config
2. Not in paper mode
3. `LimitChaser` successfully initialized

**Exit orders** (stop loss, take profit) continue to use standard execution for reliability.

## Metrics & Observability

The `LimitChaseResult` provides detailed execution metrics:
- `success`: Whether order was filled
- `filled_price`: Actual fill price
- `slippage_bps`: Slippage in basis points
- `total_chases`: Number of price chases performed
- `reason`: Success/failure reason

These metrics are logged and can be integrated into Prometheus for monitoring.

## Future Enhancements

1. **Adaptive Timeout**: Adjust timeout based on volatility
2. **Volume-Weighted Pricing**: Use VWAP for better fills
3. **Multi-Leg Support**: Extend to spreads/strangles
4. **Machine Learning**: Learn optimal chase parameters per instrument

## Testing

To test limit chase:
1. Enable in config: `use_limit_chase: true`
2. Place a test order in LIVE mode
3. Monitor logs for limit chase activity
4. Verify slippage is within threshold

## Notes

- Limit chase is **disabled in paper mode** (instant fills)
- Only used for **entry orders** (exits use standard execution)
- Falls back gracefully to standard execution on any error
- Compatible with existing OCO, retry, and rate limiting logic

