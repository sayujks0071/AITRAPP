# 🧠 HiveMind MCP Usage Guide

## Quick Start

Your HiveMind is now connected to Kite MCP tools! Here's how to use it:

### Basic Usage

```python
from packages.core.hivemind.swarm import HiveMindSwarm
from packages.core.hivemind.kite_mcp_adapter import KiteMCPAdapter
from packages.core.config import Settings
from kiteconnect import KiteConnect
from dotenv import load_dotenv

# Load environment
load_dotenv()
settings = Settings()

# Create adapter
kite = KiteConnect(api_key=settings.kite_api_key)
kite.set_access_token(settings.kite_access_token)
adapter = KiteMCPAdapter(kite_client=kite)

# Initialize HiveMind with MCP adapter
hive = HiveMindSwarm(
    config_path="configs/kite_day1_live.yaml",
    kite_mcp_adapter=adapter
)

# Build context
context = {
    "timestamp": datetime.now().isoformat(),
    "vix": 15.5,
    "trend": "SIDEWAYS",
    # ... your context
}

# Run council meeting (automatically enriched with MCP data!)
report = hive.run_council_meeting(context)
```

## Adapter API

### `get_portfolio_summary()`

Returns a rich context summary for the Council meeting:

```python
portfolio = adapter.get_portfolio_summary()

# Response format:
{
    "status": "success",
    "data": {
        "capital": {
            "available": 500000.0,  # Available cash
            "used": 200000.0,     # Margin used
            "pnl_day": 5000.0      # Day's PnL
        },
        "positions": {
            "count": 5,            # Open positions count
            "net_exposure": 150000.0  # Net exposure
        },
        "timestamp": "live"
    }
}
```

### `get_market_quote(instruments)`

Fetches live quotes for symbols:

```python
quotes = adapter.get_market_quote(['NSE:INFY', 'NSE:SBIN'])

# Response format:
{
    "status": "success",
    "data": {
        "NSE:INFY": {...},  # Quote data
        "NSE:SBIN": {...}
    }
}
```

## Automatic Context Enrichment

When you pass `kite_mcp_adapter` to HiveMind, it automatically:

1. **Calls `get_portfolio_summary()`** before each council meeting
2. **Merges data into context**:
   - `portfolio_risk.available_margin` ← capital.available
   - `portfolio_risk.used_margin` ← capital.used
   - `portfolio_risk.daily_pnl` ← capital.pnl_day
   - `portfolio_risk.margin_utilization_pct` ← calculated
3. **All 7 agents receive enriched context** with real-time Kite data

## Modes

The adapter works in two modes:

### SDK Mode (Default)
- Uses KiteConnect SDK directly
- No MCP server required
- Works immediately with your existing setup

### MCP Mode
- Uses Model Context Protocol tools
- Requires MCP client configuration
- Provides standardized AI interface

The adapter automatically falls back to SDK mode if MCP is unavailable.

## Running the Example

```bash
python3 scripts/run_hivemind_mcp.py
```

This will:
- ✅ Create adapter from .env credentials
- ✅ Initialize HiveMind with MCP adapter
- ✅ Test adapter connection
- ✅ Run council meeting with real-time data

## Response Format

All adapter methods return a consistent format:

```python
{
    "status": "success" | "error",
    "data": {...},  # If success
    "message": "..."  # If error
}
```

This makes it easy to handle both success and error cases.

## Integration Points

The adapter integrates with:

1. **HiveMindSwarm**: Automatic context enrichment
2. **All 7 Agents**: Receive enriched context
3. **RiskAgent**: Uses margin and PnL data
4. **MarketAgent**: Can use market quotes
5. **StrategyAgent**: Can use position data

## Next Steps

1. **Test**: Run `python3 scripts/run_hivemind_mcp.py`
2. **Monitor**: Check logs for MCP data enrichment
3. **Extend**: Add more adapter methods as needed
4. **Configure MCP**: Set up MCP server for direct MCP mode (optional)

Your HiveMind is now connected! 🚀


