#!/usr/bin/env python3
"""
Run HiveMind with MCP Integration
==================================

Ready-to-use script that connects HiveMind to Kite MCP tools using your existing configuration.

Usage:
    python3 scripts/run_hivemind_mcp.py
"""

import sys
import os
from datetime import datetime
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from packages.core.hivemind.swarm import HiveMindSwarm
from packages.core.hivemind.kite_mcp_adapter import KiteMCPAdapter
from packages.core.hivemind.mcp_client import MCPClient
from packages.core.config import Settings
from kiteconnect import KiteConnect

# Load environment variables
load_dotenv()


def create_kite_mcp_adapter_from_env():
    """
    Create KiteMCPAdapter using credentials from .env file.
    
    Returns:
        KiteMCPAdapter instance
    """
    # Load settings from environment
    settings = Settings()
    
    # Option 1: Try MCP client (if configured)
    mcp_client = None
    server_url = os.getenv("MCP_SERVER_URL")
    if server_url:
        try:
            mcp_client = MCPClient(server_url=server_url)
            print("✅ MCP client initialized from server URL")
        except Exception as e:
            print(f"⚠️  MCP client initialization failed: {e}")
    
    # Option 2: Fallback to KiteConnect SDK (using your existing config)
    kite_client = None
    if not mcp_client:
        try:
            api_key = settings.kite_api_key
            access_token = settings.kite_access_token
            
            if not api_key or not access_token:
                print("⚠️  KITE_API_KEY or KITE_ACCESS_TOKEN not found in .env")
                print("   Using adapter without Kite client (limited functionality)")
            else:
                kite = KiteConnect(api_key=api_key)
                kite.set_access_token(access_token)
                kite_client = kite
                print("✅ KiteConnect SDK initialized from .env")
        except Exception as e:
            print(f"⚠️  KiteConnect initialization failed: {e}")
            print("   Using adapter without Kite client (limited functionality)")
    
    # Create adapter
    adapter = KiteMCPAdapter(mcp_client=mcp_client, kite_client=kite_client)
    return adapter


def build_default_context():
    """
    Build default context for HiveMind council meeting.
    
    Returns:
        Dictionary with default context
    """
    return {
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
            "avg_slippage": 0.0,
            "avg_limit_chase_savings_bps": 0.0,
            "chase_savings": 0.0,
            "fill_rate": 1.0,
            "avg_order_latency_ms": 0.0
        }
    }


def main():
    """Main function"""
    print("\n" + "="*70)
    print("🧠 HIVEMIND WITH MCP INTEGRATION")
    print("="*70)
    print()
    
    # Step 1: Create adapter from environment
    print("📡 Step 1: Creating Kite MCP Adapter from .env...")
    adapter = create_kite_mcp_adapter_from_env()
    print()
    
    # Step 2: Find config file
    print("📋 Step 2: Finding config file...")
    config_paths = [
        "configs/kite_day1_live.yaml",
        "configs/kite_canary_live.yaml",
        "configs/kite_live.yaml"
    ]
    config_path = None
    for path in config_paths:
        if os.path.exists(path):
            config_path = path
            print(f"   ✅ Found: {path}")
            break
    
    if not config_path:
        print("   ⚠️  No config file found, using default")
        config_path = "configs/kite_day1_live.yaml"
    print()
    
    # Step 3: Initialize HiveMind
    print("🧠 Step 3: Initializing HiveMind Swarm...")
    try:
        hive = HiveMindSwarm(config_path=config_path, kite_mcp_adapter=adapter)
        print("   ✅ HiveMind Swarm initialized")
    except Exception as e:
        print(f"   ❌ Failed to initialize HiveMind: {e}")
        return
    print()
    
    # Step 4: Test adapter
    print("🔍 Step 4: Testing MCP adapter...")
    try:
        portfolio = adapter.get_portfolio_summary()
        if portfolio.get("status") == "success":
            data = portfolio.get("data", {})
            capital = data.get("capital", {})
            positions_data = data.get("positions", {})
            
            print(f"   ✅ Portfolio Summary Retrieved:")
            print(f"      - Margin Available: ₹{capital.get('available', 0):,.0f}")
            print(f"      - Margin Used: ₹{capital.get('used', 0):,.0f}")
            print(f"      - Day PnL: ₹{capital.get('pnl_day', 0):,.2f}")
            print(f"      - Open Positions: {positions_data.get('count', 0)}")
            print(f"      - Net Exposure: ₹{positions_data.get('net_exposure', 0):,.0f}")
        else:
            print(f"   ⚠️  Adapter test failed: {portfolio.get('message', 'Unknown error')}")
    except Exception as e:
        print(f"   ⚠️  Adapter test failed: {e}")
    print()
    
    # Step 5: Run council meeting
    print("🎯 Step 5: Running HiveMind Council Meeting...")
    print("   (Context will be enriched with MCP data automatically)")
    print()
    
    context = build_default_context()
    
    try:
        report = hive.run_council_meeting(context)
        
        # Display results
        print("📊 Council Meeting Results:")
        print(f"   Final Directive: {report.get('final_directive', 'N/A')}")
        reasoning = report.get('reasoning', 'N/A')
        if len(reasoning) > 150:
            reasoning = reasoning[:150] + "..."
        print(f"   Reasoning: {reasoning}")
        print()
        
        # Show approved allocations
        allocations = report.get('approved_allocations', {})
        if allocations:
            print("   📈 Approved Allocations:")
            for strategy, weight in allocations.items():
                print(f"      - {strategy}: {weight:.2%}")
            print()
        
        # Show agent insights summary
        agent_insights = report.get('agent_insights', {})
        if agent_insights:
            print("   👥 Agent Insights Summary:")
            for agent_name, insight in agent_insights.items():
                if isinstance(insight, dict):
                    # Try to extract key information
                    if 'defcon_level' in insight:
                        print(f"      - {agent_name}: DEFCON {insight['defcon_level']}")
                    elif 'regime' in insight:
                        print(f"      - {agent_name}: {insight['regime']}")
                    elif 'recommendations' in insight:
                        recs = insight['recommendations']
                        if recs:
                            print(f"      - {agent_name}: {len(recs)} recommendations")
                    else:
                        keys = list(insight.keys())[:2]
                        print(f"      - {agent_name}: {', '.join(keys)}")
            print()
        
    except Exception as e:
        print(f"   ❌ Council meeting failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print("="*70)
    print("✅ HiveMind with MCP integration complete!")
    print("="*70)
    print()
    
    print("💡 Notes:")
    print("   - MCP data is automatically merged into context before council meeting")
    print("   - If MCP unavailable, adapter falls back to KiteConnect SDK")
    print("   - Check logs for detailed MCP tool calls and data enrichment")
    print()


if __name__ == "__main__":
    main()

