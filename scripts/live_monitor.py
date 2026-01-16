#!/usr/bin/env python3
"""
Live Monitoring Dashboard
A Python-based TUI for monitoring the trading system.
"""

import sys
import os
import time
import json
from datetime import datetime
import shutil

# Check if requests is installed
try:
    import requests
except ImportError:
    print("❌ 'requests' library not found. Please install it: pip install requests")
    sys.exit(1)

API_URL = os.getenv("API_URL", "http://localhost:8000")

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def get_metrics():
    try:
        response = requests.get(f"{API_URL}/metrics", timeout=2)
        if response.status_code == 200:
            lines = response.text.split('\n')
            metrics = {}
            for line in lines:
                if line and not line.startswith('#'):
                    parts = line.split()
                    if len(parts) >= 2:
                        key = parts[0]
                        val = parts[1]
                        # Handle labeled metrics
                        if '{' in key:
                            base_key = key.split('{')[0]
                            metrics[base_key] = float(val)
                        else:
                            metrics[key] = float(val)
            return metrics
    except Exception:
        pass
    return {}

def get_health():
    try:
        response = requests.get(f"{API_URL}/health", timeout=2)
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return None

def print_dashboard():
    while True:
        try:
            metrics = get_metrics()
            health = get_health()

            clear_screen()
            width = shutil.get_terminal_size().columns
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            print("=" * width)
            print(f" 🚀 AITRAPP LIVE MONITORING - {timestamp}".center(width))
            print("=" * width)
            print("")

            # System Status
            print(" 🏥 SYSTEM STATUS")
            print(" " + "-" * 20)

            if health:
                status_color = "✅" if health.get("status") == "healthy" else "❌"
                mode = health.get("mode", "UNKNOWN")
                print(f"   Status: {status_color} {health.get('status')} ({mode})")
            else:
                print("   Status: ❌ UNREACHABLE")

            leader_status = metrics.get('trader_is_leader', 0)
            leader_icon = "👑" if leader_status == 1 else "💤"
            print(f"   Leader: {leader_icon} {'Active' if leader_status == 1 else 'Standby'}")
            print("")

            # Heartbeats
            print(" 💓 HEARTBEATS")
            print(" " + "-" * 20)

            md_hb = metrics.get('trader_marketdata_heartbeat_seconds', 999)
            os_hb = metrics.get('trader_order_stream_heartbeat_seconds', 999)

            md_status = "✅" if md_hb < 5 else "⚠️ "
            os_status = "✅" if os_hb < 5 else "⚠️ "

            print(f"   Market Data:  {md_status} {md_hb:.2f}s ago")
            print(f"   Order Stream: {os_status} {os_hb:.2f}s ago")
            print("")

            # Trading Stats
            print(" 📊 TRADING ACTIVITY")
            print(" " + "-" * 20)

            signals = int(metrics.get('trader_signals_total', 0))
            decisions = int(metrics.get('trader_decisions_total', 0))
            orders_placed = int(metrics.get('trader_orders_placed_total', 0))
            orders_filled = int(metrics.get('trader_orders_filled_total', 0))

            print(f"   Signals Generated: {signals}")
            print(f"   Decisions Planned: {decisions}")
            print(f"   Orders Placed:     {orders_placed}")
            print(f"   Orders Filled:     {orders_filled}")
            print("")

            # Risk & PnL
            print(" 💰 RISK & PnL")
            print(" " + "-" * 20)

            pnl = metrics.get('trader_daily_pnl_rupees', 0.0)
            heat = metrics.get('trader_portfolio_heat_rupees', 0.0)

            pnl_color = "🟢" if pnl >= 0 else "🔴"

            print(f"   Daily PnL:      {pnl_color} ₹ {pnl:,.2f}")
            print(f"   Portfolio Heat: 🔥 ₹ {heat:,.2f}")
            print("")

            print("=" * width)
            print(" Press Ctrl+C to exit".center(width))

            time.sleep(1)

        except KeyboardInterrupt:
            print("\nExiting...")
            sys.exit(0)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    print_dashboard()
