#!/usr/bin/env python3
"""
Live System Monitor - Real-time monitoring of AITRAPP trading system
====================================================================

Monitors key system metrics and displays them in real-time.
"""

import time
import requests
import json
from datetime import datetime
from typing import Dict, Any

API_BASE = "http://localhost:8000"

def get_health() -> Dict[str, Any]:
    """Get system health status"""
    try:
        resp = requests.get(f"{API_BASE}/health", timeout=2)
        return resp.json() if resp.status_code == 200 else {}
    except:
        return {}

def get_state() -> Dict[str, Any]:
    """Get system state"""
    try:
        resp = requests.get(f"{API_BASE}/state", timeout=2)
        return resp.json() if resp.status_code == 200 else {}
    except:
        return {}

def get_positions() -> list:
    """Get current positions"""
    try:
        resp = requests.get(f"{API_BASE}/positions", timeout=2)
        return resp.json() if resp.status_code == 200 else []
    except:
        return []

def get_execution_stats() -> Dict[str, Any]:
    """Get execution engine stats"""
    try:
        resp = requests.get(f"{API_BASE}/api/execution/stats", timeout=2)
        return resp.json() if resp.status_code == 200 else {}
    except:
        return {}

def get_strategy_summary() -> list:
    """Get strategy summary"""
    try:
        resp = requests.get(f"{API_BASE}/api/strategies/summary", timeout=2)
        data = resp.json() if resp.status_code == 200 else {}
        return data.get("strategies", [])
    except:
        return []

def format_pnl(pnl: float) -> str:
    """Format PnL with color indicators"""
    if pnl > 0:
        return f"✅ +₹{pnl:,.2f}"
    elif pnl < 0:
        return f"❌ ₹{pnl:,.2f}"
    return f"⚪ ₹{pnl:,.2f}"

def main():
    """Main monitoring loop"""
    print("=" * 80)
    print("🚀 AITRAPP LIVE SYSTEM MONITOR")
    print("=" * 80)
    print("Press Ctrl+C to stop\n")
    
    try:
        while True:
            # Clear screen (works in most terminals)
            print("\033[2J\033[H", end="")
            
            # Get data
            health = get_health()
            state = get_state()
            positions = get_positions()
            exec_stats = get_execution_stats()
            strategies = get_strategy_summary()
            
            # Header
            print("=" * 80)
            print(f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("=" * 80)
            
            # System Health
            print("\n📊 SYSTEM HEALTH")
            print("-" * 80)
            mode = health.get("mode", "UNKNOWN")
            status = health.get("status", "UNKNOWN")
            is_paused = state.get("is_paused", False)
            market_open = state.get("is_market_open", False)
            
            mode_icon = "🟢" if mode == "LIVE" else "🟡"
            status_icon = "✅" if status == "healthy" else "⚠️"
            pause_icon = "⏸️" if is_paused else "▶️"
            market_icon = "🟢" if market_open else "🔴"
            
            print(f"  Mode: {mode_icon} {mode}")
            print(f"  Status: {status_icon} {status}")
            print(f"  Trading: {pause_icon} {'PAUSED' if is_paused else 'ACTIVE'}")
            print(f"  Market: {market_icon} {'OPEN' if market_open else 'CLOSED'}")
            print(f"  WebSocket: {'✅ Connected' if state.get('websocket_connected') else '❌ Disconnected'}")
            print(f"  Market Data: {'✅ Connected' if state.get('marketdata_connected') else '❌ Disconnected'}")
            
            # Trading Stats
            print("\n💰 TRADING STATS")
            print("-" * 80)
            daily_pnl = state.get("daily_pnl", 0.0)
            trades_today = state.get("trades_today", 0)
            win_rate = state.get("win_rate", 0.0)
            positions_count = state.get("positions_count", 0)
            
            print(f"  Daily PnL: {format_pnl(daily_pnl)}")
            print(f"  Trades Today: {trades_today}")
            print(f"  Win Rate: {win_rate:.1f}%")
            print(f"  Open Positions: {positions_count}")
            
            # Execution Stats
            print("\n⚙️  EXECUTION ENGINE")
            print("-" * 80)
            attempts = exec_stats.get("attempts", 0)
            fills = exec_stats.get("fills", 0)
            errors = exec_stats.get("errors", 0)
            saved_slippage = exec_stats.get("saved_slippage_rs", 0.0)
            
            fill_rate = (fills / attempts * 100) if attempts > 0 else 0.0
            print(f"  Attempts: {attempts}")
            print(f"  Fills: {fills} ({fill_rate:.1f}%)")
            print(f"  Errors: {errors}")
            print(f"  Slippage Saved: ₹{saved_slippage:,.2f}")
            
            # Active Positions
            if positions and isinstance(positions, list):
                print("\n📈 ACTIVE POSITIONS")
                print("-" * 80)
                for pos in positions[:5]:  # Show first 5
                    if isinstance(pos, dict):
                        symbol = pos.get("symbol", "N/A")
                        qty = pos.get("quantity", 0)
                        pnl = pos.get("unrealised_pnl", 0.0)
                        print(f"  {symbol}: {qty} @ {format_pnl(pnl)}")
                if len(positions) > 5:
                    print(f"  ... and {len(positions) - 5} more")
            
            # Strategy Status
            if strategies and isinstance(strategies, list):
                print("\n🎯 STRATEGY STATUS")
                print("-" * 80)
                enabled_strats = [s for s in strategies if isinstance(s, dict) and s.get("enabled", False)]
                for strat in enabled_strats[:5]:  # Show first 5
                    name = strat.get("name", "Unknown")
                    pnl = strat.get("realised_pnl", 0) + strat.get("unrealised_pnl", 0)
                    alloc = strat.get("current_allocation_pct", 0.0)
                    print(f"  {name}: {format_pnl(pnl)} (Alloc: {alloc:.1f}%)")
            
            # Footer
            print("\n" + "=" * 80)
            print("Monitoring... (Refresh every 5 seconds)")
            print("=" * 80)
            
            time.sleep(5)
            
    except KeyboardInterrupt:
        print("\n\n👋 Monitoring stopped.")
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    main()

