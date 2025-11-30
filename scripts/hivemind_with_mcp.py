#!/usr/bin/env python3
"""
HiveMind with MCP Integration Example
=====================================

Demonstrates how to connect HiveMind to Kite MCP tools.

This script shows:
1. How to initialize KiteMCPAdapter
2. How to pass it to HiveMindSwarm
3. How HiveMind agents can use MCP tools for real-time data

Usage:
    python3 scripts/hivemind_with_mcp.py
"""

import sys
import os
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from packages.core.hivemind.swarm import HiveMindSwarm
from packages.core.hivemind.kite_mcp_adapter import KiteMCPAdapter
from packages.core.hivemind.mcp_client import MCPClient
from kiteconnect import KiteConnect

# Load environment variables
load_dotenv()


def create_kite_mcp_adapter():
    """
    Create KiteMCPAdapter with MCP client or KiteConnect fallback.
    
    Returns:
        KiteMCPAdapter instance
    """
    # Option 1: Use MCP client (if MCP server is available)
    mcp_client = None
    try:
        # Try to create MCP client
        # In production, you would configure this with your MCP server details
        server_url = os.getenv("MCP_SERVER_URL")
        if server_url:
            mcp_client = MCPClient(server_url=server_url)
            print("✅ MCP client initialized")
    except Exception as e:
        print(f"⚠️  MCP client initialization failed: {e}")
    
    # Option 2: Fallback to KiteConnect SDK
    kite_client = None
    if not mcp_client:
        try:
            api_key = os.getenv("KITE_API_KEY")
            access_token = os.getenv("KITE_ACCESS_TOKEN")
            
            if api_key and access_token:
                kite = KiteConnect(api_key=api_key)
                kite.set_access_token(access_token)
                kite_client = kite
                print("✅ KiteConnect SDK fallback initialized")
        except Exception as e:
            print(f"⚠️  KiteConnect initialization failed: {e}")
    
    # Create adapter
    adapter = KiteMCPAdapter(mcp_client=mcp_client, kite_client=kite_client)
    return adapter


def main():
    """Main function demonstrating HiveMind with MCP integration"""
    print("\n" + "="*70)
    print("🧠 HIVEMIND WITH MCP INTEGRATION")
    print("="*70)
    print()
    
    # Step 1: Create Kite MCP adapter
    print("📡 Step 1: Creating Kite MCP Adapter...")
    adapter = create_kite_mcp_adapter()
    print()
    
    # Step 2: Initialize HiveMind with MCP adapter
    print("🧠 Step 2: Initializing HiveMind Swarm with MCP adapter...")
    config_path = "configs/kite_day1_live.yaml"
    if not os.path.exists(config_path):
        config_path = "configs/kite_canary_live.yaml"
    
    hive = HiveMindSwarm(config_path=config_path, kite_mcp_adapter=adapter)
    print()
    
    # Step 3: Test MCP adapter directly
    print("🔍 Step 3: Testing MCP adapter...")
    try:
        # Get portfolio summary
        portfolio = adapter.get_portfolio_summary()
        if portfolio.get("status") == "success":
            data = portfolio.get("data", {})
            capital = data.get("capital", {})
            positions_data = data.get("positions", {})
            
            print(f"   Portfolio Summary:")
            print(f"   - Margin Available: ₹{capital.get('available', 0):,.0f}")
            print(f"   - Margin Used: ₹{capital.get('used', 0):,.0f}")
            print(f"   - Day PnL: ₹{capital.get('pnl_day', 0):,.2f}")
            print(f"   - Open Positions: {positions_data.get('count', 0)}")
            print(f"   - Net Exposure: ₹{positions_data.get('net_exposure', 0):,.0f}")
        else:
            print(f"   ⚠️  Portfolio summary failed: {portfolio.get('message', 'Unknown error')}")
    except Exception as e:
        print(f"   ⚠️  Portfolio summary failed: {e}")
    print()
    
    # Step 4: Run HiveMind council meeting
    print("🎯 Step 4: Running HiveMind Council Meeting...")
    print()
    
    # Build context (HiveMind will enrich it with MCP data if adapter is available)
    from datetime import datetime
    context = {
        "timestamp": datetime.now().isoformat(),
        "vix": 15.5,
        "trend": "SIDEWAYS",
        "events": "None",
        "market_regime": "UNKNOWN",
        "net_delta": 0,
        "pnl": 0.0,
        "margin_used": 0.0,
        "portfolio_risk": {
            "daily_pnl": 0.0,
            "portfolio_heat_pct": 0.0,
            "available_margin": 0.0,
            "margin_utilization_pct": 0.0,
            "net_liquid": 1000000.0,
            "used_margin": 0.0
        },
        "strategy_metrics": {},
        "execution_stats": {
            "avg_slippage_bps": 0.0,
            "fill_rate": 1.0
        }
    }
    
    # Run council meeting
    report = hive.run_council_meeting(context)
    
    # Display results
    print("📊 Council Meeting Results:")
    print(f"   Final Directive: {report.get('final_directive', 'N/A')}")
    print(f"   Reasoning: {report.get('reasoning', 'N/A')[:100]}...")
    print()
    
    # Show agent insights
    agent_insights = report.get('agent_insights', {})
    if agent_insights:
        print("👥 Agent Insights:")
        for agent_name, insight in agent_insights.items():
            if isinstance(insight, dict):
                key = list(insight.keys())[0] if insight else "N/A"
                print(f"   - {agent_name}: {key}")
    print()
    
    print("="*70)
    print("✅ HiveMind with MCP integration complete!")
    print("="*70)
    print()
    
    print("💡 Next Steps:")
    print("   1. Configure MCP server connection in .env (MCP_BRIDGE_SCRIPT)")
    print("   2. HiveMind agents will automatically use MCP data when available")
    print("   3. Check logs for MCP tool calls and data enrichment")
    print()


if __name__ == "__main__":
    main()

