#!/usr/bin/env python3
"""
Restart Market Data WebSocket Connection
========================================

This script restarts the market data WebSocket connection to fix stale heartbeat issues.
It can be called via API or run directly.

Usage:
    python3 scripts/restart_market_data.py
"""

import requests
import sys

API_BASE = "http://localhost:8000"

def restart_market_data():
    """Restart market data stream via API"""
    try:
        # Check if there's a restart endpoint
        # If not, we'll need to restart the API
        response = requests.post(f"{API_BASE}/market-data/restart", timeout=5)
        if response.status_code == 200:
            print("✅ Market data stream restarted via API")
            return True
        else:
            print(f"⚠️  API endpoint returned {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Error calling API: {e}")
        print("\n💡 Market data will restart automatically when:")
        print("   1. Market opens (9:15 AM IST)")
        print("   2. API is restarted")
        print("   3. WebSocket reconnects automatically")
        return False

if __name__ == "__main__":
    restart_market_data()

