# 🚀 HiveMind MCP Quick Start

## Quick Integration (3 Steps)

### Step 1: Import and Create Adapter

```python
from packages.core.hivemind.swarm import HiveMindSwarm
from packages.core.hivemind.kite_mcp_adapter import KiteMCPAdapter
from kiteconnect import KiteConnect

# Create KiteConnect client (fallback)
kite = KiteConnect(api_key="your_key")
kite.set_access_token("your_token")

# Create adapter
adapter = KiteMCPAdapter(kite_client=kite)
```

### Step 2: Initialize HiveMind with Adapter

```python
hive = HiveMindSwarm(
    config_path="configs/kite_day1_live.yaml",
    kite_mcp_adapter=adapter  # ← Add this!
)
```

### Step 3: Run Council Meeting

```python
context = {...}  # Your trading context
report = hive.run_council_meeting(context)
# HiveMind now has access to real-time Kite data via MCP!
```

## What Happens Automatically?

When you pass `kite_mcp_adapter` to HiveMind:

✅ **Context Enrichment**: Portfolio data, margins, positions automatically added  
✅ **Real-time Delta**: Net delta calculated from live positions  
✅ **Margin Info**: Current margin utilization from Kite  
✅ **Position Data**: All open positions included in context  

## Available MCP Tools

The adapter provides access to all Kite MCP tools:

- `get_quotes()` - Market quotes
- `get_ltp()` - Latest prices
- `get_positions()` - Current positions
- `get_holdings()` - Equity holdings
- `get_margins()` - Margin info
- `get_orders()` - All orders
- `get_trades()` - Trading history
- `get_profile()` - User profile
- `get_portfolio_summary()` - Complete portfolio snapshot

## Test It

```bash
python3 scripts/hivemind_with_mcp.py
```

## Full Documentation

See `HIVEMIND_MCP_INTEGRATION.md` for complete details.


