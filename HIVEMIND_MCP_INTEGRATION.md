# 🧠 HiveMind MCP Integration Guide

## Overview

This guide explains how to connect your **HiveMind** (Level 7 Multi-Agent System) to **Kite MCP tools** for real-time trading data access.

## What is This Integration?

The HiveMind MCP integration allows your 7-agent council to:
- Access real-time market data through MCP tools
- Get portfolio positions, margins, and PnL via MCP
- Query orders, trades, and holdings through MCP
- Fall back to KiteConnect SDK if MCP is unavailable

## Architecture

```
┌─────────────────┐
│  HiveMindSwarm  │
│  (7 Agents)     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ KiteMCPAdapter  │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌────────┐ ┌──────────────┐
│  MCP   │ │ KiteConnect  │
│ Client │ │ SDK (fallback)│
└────────┘ └──────────────┘
```

## Components

### 1. KiteMCPAdapter

Located at: `packages/core/hivemind/kite_mcp_adapter.py`

Provides unified interface for:
- **Market Data**: `get_quotes()`, `get_ltp()`, `get_ohlc()`
- **Portfolio**: `get_positions()`, `get_holdings()`, `get_margins()`
- **Orders**: `get_orders()`, `get_trades()`
- **Profile**: `get_profile()`
- **Search**: `search_instruments()`
- **Summary**: `get_portfolio_summary()` (comprehensive portfolio snapshot)

### 2. MCPClient

Located at: `packages/core/hivemind/mcp_client.py`

Python client for calling MCP tools. Can work in two modes:
- **Direct Mode**: Connects to MCP server directly
- **Bridge Mode**: Uses a bridge script/service

### 3. HiveMindSwarm Integration

The `HiveMindSwarm` class now accepts an optional `kite_mcp_adapter` parameter:

```python
from packages.core.hivemind.swarm import HiveMindSwarm
from packages.core.hivemind.kite_mcp_adapter import KiteMCPAdapter

# Create adapter
adapter = KiteMCPAdapter(mcp_client=mcp_client, kite_client=kite_client)

# Initialize HiveMind with adapter
hive = HiveMindSwarm(
    config_path="configs/kite_day1_live.yaml",
    kite_mcp_adapter=adapter
)
```

## Usage Examples

### Example 1: Basic Integration

```python
#!/usr/bin/env python3
from packages.core.hivemind.swarm import HiveMindSwarm
from packages.core.hivemind.kite_mcp_adapter import KiteMCPAdapter
from kiteconnect import KiteConnect

# Create KiteConnect client (fallback)
kite = KiteConnect(api_key="your_api_key")
kite.set_access_token("your_access_token")

# Create adapter with KiteConnect fallback
adapter = KiteMCPAdapter(kite_client=kite)

# Initialize HiveMind
hive = HiveMindSwarm(
    config_path="configs/kite_day1_live.yaml",
    kite_mcp_adapter=adapter
)

# Run council meeting (will use MCP data if available)
context = {...}  # Your trading context
report = hive.run_council_meeting(context)
```

### Example 2: With MCP Client

```python
from packages.core.hivemind.mcp_client import MCPClient
from packages.core.hivemind.kite_mcp_adapter import KiteMCPAdapter

# Create MCP client (if you have MCP server running)
mcp_client = MCPClient(bridge_script="/path/to/mcp_bridge.py")

# Create adapter with MCP client
adapter = KiteMCPAdapter(mcp_client=mcp_client)

# Use with HiveMind
hive = HiveMindSwarm(
    config_path="configs/kite_day1_live.yaml",
    kite_mcp_adapter=adapter
)
```

### Example 3: Direct Adapter Usage

You can also use the adapter directly in your agents or scripts:

```python
from packages.core.hivemind.kite_mcp_adapter import KiteMCPAdapter

adapter = KiteMCPAdapter(kite_client=kite)

# Get portfolio summary
portfolio = adapter.get_portfolio_summary()
print(f"Net Delta: {portfolio['net_delta']}")
print(f"Margin Used: {portfolio['margins']['used']}")

# Get quotes
quotes = adapter.get_quotes(['NSE:INFY', 'NSE:SBIN'])

# Get positions
positions = adapter.get_positions()
```

## Available MCP Tools

The adapter supports all Kite MCP tools:

### Market Data
- `mcp_kite_get_quotes` - Full market quotes
- `mcp_kite_get_ltp` - Latest trading prices
- `mcp_kite_get_ohlc` - OHLC data
- `mcp_kite_get_historical_data` - Historical price data

### Portfolio
- `mcp_kite_get_positions` - Current positions
- `mcp_kite_get_holdings` - Equity holdings
- `mcp_kite_get_margins` - Margin information

### Orders
- `mcp_kite_get_orders` - All orders
- `mcp_kite_get_order_history` - Order history
- `mcp_kite_get_order_trades` - Order trades
- `mcp_kite_get_trades` - Trading history
- `mcp_kite_get_gtts` - GTT orders

### Profile & Search
- `mcp_kite_get_profile` - User profile
- `mcp_kite_search_instruments` - Instrument search

## How HiveMind Uses MCP Data

When you pass `kite_mcp_adapter` to `HiveMindSwarm`, it automatically:

1. **Enriches Context**: Before each council meeting, it calls `get_portfolio_summary()` to get real-time data
2. **Updates Portfolio Risk**: Merges MCP data into the context's `portfolio_risk` dictionary
3. **Updates Net Delta**: Gets real-time delta from positions
4. **Updates Positions**: Includes current positions in context

The agents then use this enriched context for decision-making.

## Configuration

### Environment Variables

Add to your `.env` file:

```bash
# MCP Configuration (optional)
MCP_SERVER_URL=http://localhost:8080/mcp

# KiteConnect SDK (fallback)
KITE_API_KEY=your_api_key
KITE_ACCESS_TOKEN=your_access_token
```

### MCP Server Connection

The `MCPClient` is currently a stub that can be extended to connect to:
- SSE (Server-Sent Events) MCP servers
- Stdio MCP servers
- HTTP/WebSocket MCP servers

When you implement the actual connection, it will:
1. Connect to the MCP server at `server_url`
2. Send JSON-RPC requests for tool calls
3. Return tool results

## Testing

Run the example script:

```bash
python3 scripts/hivemind_with_mcp.py
```

This will:
1. Create a KiteMCPAdapter
2. Initialize HiveMind with the adapter
3. Test the adapter directly
4. Run a council meeting with MCP data

## Benefits

1. **Unified Interface**: Same API whether using MCP or KiteConnect SDK
2. **Automatic Fallback**: Falls back to KiteConnect if MCP unavailable
3. **Real-time Data**: HiveMind agents get fresh data from Kite
4. **Modular**: Can be added/removed without changing agent code
5. **Future-proof**: Easy to switch to full MCP when available

## Troubleshooting

### MCP Client Not Available

If MCP client initialization fails, the adapter will automatically use KiteConnect SDK fallback. Check logs for:
```
⚠️  MCP client initialization failed: ...
✅ KiteConnect SDK fallback initialized
```

### No Data Returned

If `get_portfolio_summary()` returns empty data:
1. Check Kite credentials are set correctly
2. Verify KiteConnect SDK is working
3. Check network connectivity to Kite API

### Bridge Script Issues

If using MCP bridge:
1. Ensure bridge script is executable: `chmod +x /path/to/mcp_bridge.py`
2. Test bridge script directly: `./mcp_bridge.py mcp_kite_get_profile '{}'`
3. Check MCP server is running and accessible

## Next Steps

1. **Test Integration**: Run `scripts/hivemind_with_mcp.py`
2. **Configure MCP**: Set up MCP server if you want direct MCP access
3. **Monitor Logs**: Check how HiveMind uses MCP data in council meetings
4. **Extend Agents**: Modify agents to use adapter for specific data needs

## Related Files

- `packages/core/hivemind/kite_mcp_adapter.py` - Main adapter
- `packages/core/hivemind/mcp_client.py` - MCP client wrapper
- `packages/core/hivemind/swarm.py` - HiveMindSwarm with MCP support
- `scripts/hivemind_with_mcp.py` - Example usage script

## Support

For issues or questions:
1. Check logs for error messages
2. Verify Kite credentials
3. Test adapter directly before using with HiveMind
4. Review MCP server configuration if using MCP mode

