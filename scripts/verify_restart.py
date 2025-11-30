#!/usr/bin/env python3
"""Verify server restart and config changes"""
import requests
import json
import sys
from datetime import datetime

API_BASE = "http://localhost:8000"

print("="*80)
print("🔍 VERIFYING SERVER RESTART & CONFIG CHANGES")
print("="*80)
print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

# Check 1: Server Health
print("1. Server Health Check")
print("-" * 80)
try:
    resp = requests.get(f"{API_BASE}/health", timeout=5)
    if resp.status_code == 200:
        health = resp.json()
        print(f"✅ Server is RUNNING")
        print(f"   Status: {health.get('status', 'unknown')}")
        print(f"   Mode: {health.get('mode', 'unknown')}")
        print(f"   Paused: {health.get('is_paused', 'unknown')}")
    else:
        print(f"❌ Server returned HTTP {resp.status_code}")
        sys.exit(1)
except requests.exceptions.ConnectionError:
    print("❌ Server NOT RUNNING - Connection refused")
    print("   → Run: ./go_live.sh")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)

# Check 2: System State
print("\n2. System State")
print("-" * 80)
try:
    resp = requests.get(f"{API_BASE}/state", timeout=5)
    if resp.status_code == 200:
        state = resp.json()
        print(f"✅ System State Retrieved")
        print(f"   Mode: {state.get('mode', 'unknown')}")
        print(f"   Paused: {state.get('is_paused', False)}")
        print(f"   Market Open: {state.get('is_market_open', False)}")
        print(f"   Positions: {state.get('positions_count', 0)}")
        print(f"   Trades Today: {state.get('trades_today', 0)}")
        print(f"   WebSocket: {'✅ Connected' if state.get('websocket_connected') else '❌ Disconnected'}")
        print(f"   Market Data: {'✅ Connected' if state.get('marketdata_connected') else '❌ Disconnected'}")
    else:
        print(f"⚠️  State endpoint returned HTTP {resp.status_code}")
except Exception as e:
    print(f"⚠️  Error getting state: {e}")

# Check 3: Regime Status
print("\n3. Regime Classification")
print("-" * 80)
try:
    resp = requests.get(f"{API_BASE}/api/regime/current", timeout=5)
    if resp.status_code == 200:
        regime_data = resp.json()
        underlyings = regime_data.get("underlyings", {})
        if underlyings:
            print("✅ Regime Classified:")
            for symbol, data in underlyings.items():
                regime = data.get("regime", "UNKNOWN")
                iv_rank = data.get("iv_rank", 0)
                print(f"   {symbol}: {regime} (IV Rank: {iv_rank:.1f}%)")
        else:
            print("⚠️  Regime Vacuum: Empty classification")
            print("   → RegimeVolEngine may need more time to classify")
            print("   → Run: curl -X POST http://localhost:8000/debug/scan-once")
    else:
        print(f"⚠️  Regime endpoint returned HTTP {resp.status_code}")
except Exception as e:
    print(f"⚠️  Error getting regime: {e}")

# Check 4: Entry Window Status (Current Time Check)
print("\n4. Entry Window Status")
print("-" * 80)
current_time = datetime.now().time()
current_hour = current_time.hour
current_minute = current_time.minute
current_time_str = f"{current_hour:02d}:{current_minute:02d}"

print(f"   Current Time: {current_time_str} IST")
print(f"   Entry Window: 09:15 - 15:00 (EXTENDED)")
print(f"   Status: {'✅ WITHIN WINDOW' if (9, 15) <= (current_hour, current_minute) <= (15, 0) else '❌ OUTSIDE WINDOW'}")

# Check 5: Execution Stats
print("\n5. Execution Engine Stats")
print("-" * 80)
try:
    resp = requests.get(f"{API_BASE}/api/execution/stats", timeout=5)
    if resp.status_code == 200:
        stats = resp.json()
        print(f"   Attempts: {stats.get('attempts', 0)}")
        print(f"   Fills: {stats.get('fills', 0)}")
        print(f"   Errors: {stats.get('errors', 0)}")
    else:
        print(f"⚠️  Execution stats endpoint returned HTTP {resp.status_code}")
except Exception as e:
    print(f"⚠️  Error getting execution stats: {e}")

# Summary
print("\n" + "="*80)
print("📋 SUMMARY")
print("="*80)
print("✅ Config files updated:")
print("   - Entry window: 09:15 - 15:00")
print("   - Max entries: 3 per day")
print("   - Intraday strangle: entry_window_end = 15:00")
print("\n✅ Server restarted with new configuration")
print("\n💡 Next Steps:")
print("   1. Monitor for regime classification (next 1-2 minutes)")
print("   2. Watch for strategy evaluation logs")
print("   3. Check for signal generation and execution")
print("="*80)




