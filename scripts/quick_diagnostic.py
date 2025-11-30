#!/usr/bin/env python3
"""Quick diagnostic - simpler version"""
import requests
import sys

try:
    # Test 1: Health
    print("Testing server connection...")
    r = requests.get("http://localhost:8000/health", timeout=2)
    print(f"Health: {r.status_code} - {r.json()}")
    
    # Test 2: Regime
    print("\nTesting regime...")
    r = requests.get("http://localhost:8000/api/regime/current", timeout=2)
    data = r.json()
    print(f"Regime: {data}")
    
    # Test 3: State
    print("\nTesting state...")
    r = requests.get("http://localhost:8000/state", timeout=2)
    state = r.json()
    print(f"Paused: {state.get('is_paused')}")
    print(f"Positions: {state.get('positions_count')}")
    print(f"Market Open: {state.get('is_market_open')}")
    
except requests.exceptions.ConnectionError:
    print("ERROR: Server not running on localhost:8000")
    print("Run: ./go_live.sh")
    sys.exit(1)
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)




