#!/usr/bin/env python3
"""
60-Second Diagnostic: Why 0 Orders at 1:00 PM?
==============================================
Identifies which safety layer is blocking execution.
"""

import requests
import json
import sys
from datetime import datetime

API_BASE = "http://localhost:8000"

def check_regime():
    """Check 1: Weather (Regime)"""
    print("\n" + "="*80)
    print("🔍 DIAGNOSTIC 1: REGIME CHECK (The Weather)")
    print("="*80)
    try:
        resp = requests.get(f"{API_BASE}/api/regime/current", timeout=5)
        data = resp.json() if resp.status_code == 200 else {}
        underlyings = data.get("underlyings", {})
        
        if not underlyings:
            print("❌ REGIME VACUUM: Empty classification")
            print("   → System is in Safety Default mode")
            print("   → All strategies requiring regime will be blocked")
            return "EMPTY"
        
        for symbol, regime_data in underlyings.items():
            regime = regime_data.get("regime", "UNKNOWN")
            iv_rank = regime_data.get("iv_rank", 0)
            atr_pct = regime_data.get("atr_pct", 0)
            
            print(f"✅ {symbol}: {regime}")
            print(f"   IV Rank: {iv_rank:.1f}% | ATR: {atr_pct:.2f}%")
            
            if regime in ["CHAOTIC", "HIGH_EVENT"]:
                print(f"   ⚠️  BLOCKED: {regime} regime is too risky")
                return "BLOCKED"
            elif regime == "UNKNOWN":
                print(f"   ⚠️  BLOCKED: Unknown regime (safety default)")
                return "BLOCKED"
            elif regime in ["LOW_MEAN_REVERT", "MEDIUM_TREND"]:
                print(f"   ✅ ALLOWED: {regime} is safe for trading")
                return "OK"
        
        return "UNKNOWN"
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return "ERROR"

def check_rejections():
    """Check 2: Rejection Reasons (from logs)"""
    print("\n" + "="*80)
    print("🔍 DIAGNOSTIC 2: REJECTION REASONS (Why No?)")
    print("="*80)
    
    import os
    from pathlib import Path
    
    log_paths = [
        "logs/trading.log",
        "logs/aitrapp_crypto.log",
        "logs/aitrapp.log"
    ]
    
    found_logs = []
    for log_path in log_paths:
        if Path(log_path).exists():
            found_logs.append(log_path)
    
    if not found_logs:
        print("⚠️  No log files found in logs/ directory")
        print("   → Logs may be going to stdout (check terminal where go_live.sh was run)")
        print("   → Or logging may not be configured to write to files")
        return []
    
    rejections = []
    for log_path in found_logs:
        try:
            with open(log_path, 'r') as f:
                lines = f.readlines()
                # Look for last 50 lines with "Skipping"
                for line in lines[-50:]:
                    if "Skipping" in line or "skipping" in line.lower():
                        rejections.append(line.strip())
        except Exception as e:
            print(f"   Error reading {log_path}: {e}")
    
    if rejections:
        print(f"✅ Found {len(rejections)} rejection messages:")
        for rej in rejections[-5:]:  # Last 5
            print(f"   → {rej}")
        
        # Analyze patterns
        reasons = {}
        for rej in rejections:
            if "REGIME" in rej:
                reasons["REGIME"] = reasons.get("REGIME", 0) + 1
            elif "EVENT" in rej:
                reasons["EVENT"] = reasons.get("EVENT", 0) + 1
            elif "WEAK_TREND" in rej or "ADX" in rej:
                reasons["WEAK_TREND"] = reasons.get("WEAK_TREND", 0) + 1
            elif "CAPITAL" in rej or "Insufficient" in rej:
                reasons["CAPITAL"] = reasons.get("CAPITAL", 0) + 1
        
        if reasons:
            print("\n   📊 Rejection Pattern:")
            for reason, count in reasons.items():
                print(f"      {reason}: {count} times")
    else:
        print("✅ No rejection messages found in recent logs")
        print("   → Strategies may not be running at all")
        print("   → Or rejections are logged differently")
    
    return rejections

def check_market_data():
    """Check 3: Market Data Feed (The Eyes)"""
    print("\n" + "="*80)
    print("🔍 DIAGNOSTIC 3: MARKET DATA FEED (The Eyes)")
    print("="*80)
    
    try:
        # Check system state for market data connection
        resp = requests.get(f"{API_BASE}/state", timeout=5)
        if resp.status_code == 200:
            state = resp.json()
            market_connected = state.get("marketdata_connected", False)
            ws_connected = state.get("websocket_connected", False)
            
            print(f"   Market Data: {'✅ Connected' if market_connected else '❌ Disconnected'}")
            print(f"   WebSocket: {'✅ Connected' if ws_connected else '❌ Disconnected'}")
            
            if not market_connected:
                print("\n   ⚠️  BLOCKED: No market data feed")
                print("   → Fix: Run ./go_live.sh again to refresh token")
                return "DISCONNECTED"
            
            return "CONNECTED"
        else:
            print(f"   ❌ ERROR: HTTP {resp.status_code}")
            return "ERROR"
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
        print("   → System may not be running")
        return "ERROR"

def check_strategy_status():
    """Check strategy enablement and allocation"""
    print("\n" + "="*80)
    print("🔍 DIAGNOSTIC 4: STRATEGY STATUS")
    print("="*80)
    
    try:
        resp = requests.get(f"{API_BASE}/api/strategies/summary", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            strategies = data.get("strategies", [])
            
            enabled = [s for s in strategies if s.get("enabled", False)]
            disabled = [s for s in strategies if not s.get("enabled", False)]
            
            print(f"   Total Strategies: {len(strategies)}")
            print(f"   Enabled: {len(enabled)}")
            print(f"   Disabled: {len(disabled)}")
            
            if disabled:
                print(f"\n   ⚠️  {len(disabled)} strategies are DISABLED:")
                for s in disabled[:3]:
                    print(f"      - {s.get('name', 'Unknown')}")
            
            if enabled:
                print(f"\n   ✅ Enabled Strategies:")
                for s in enabled[:5]:
                    name = s.get("name", "Unknown")
                    alloc = s.get("current_allocation_pct", 0.0)
                    pnl = s.get("realised_pnl", 0) + s.get("unrealised_pnl", 0)
                    print(f"      - {name}: Alloc={alloc:.1f}%, PnL=₹{pnl:.2f}")
            
            return len(enabled) > 0
        else:
            print(f"   ❌ ERROR: HTTP {resp.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
        return False

def main():
    print("="*80)
    print("🚨 60-SECOND DIAGNOSTIC: Why 0 Orders at 1:00 PM?")
    print("="*80)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Run diagnostics
    regime_status = check_regime()
    rejections = check_rejections()
    market_status = check_market_data()
    strategies_ok = check_strategy_status()
    
    # Summary
    print("\n" + "="*80)
    print("📋 DIAGNOSTIC SUMMARY")
    print("="*80)
    
    issues = []
    if regime_status in ["EMPTY", "BLOCKED"]:
        issues.append("❌ Regime Vacuum or Blocked Regime")
    if not market_status == "CONNECTED":
        issues.append("❌ Market Data Disconnected")
    if not strategies_ok:
        issues.append("❌ No Strategies Enabled")
    if not rejections:
        issues.append("⚠️  No Rejection Logs Found (may be normal)")
    
    if issues:
        print("\n🔴 IDENTIFIED ISSUES:")
        for issue in issues:
            print(f"   {issue}")
    else:
        print("\n✅ No obvious issues found")
        print("   → System may be correctly standing aside")
        print("   → Market conditions may not meet strategy criteria")
    
    print("\n" + "="*80)
    print("💡 RECOMMENDATIONS")
    print("="*80)
    
    if regime_status == "EMPTY":
        print("1. Force Regime Classification:")
        print("   curl -X POST http://localhost:8000/debug/scan-once")
        print("   (Wait 2-3 minutes for RegimeVolEngine to classify)")
    elif regime_status == "BLOCKED":
        print("1. Regime is too risky - System is correctly standing aside")
        print("   → Do NOT override safety protocols")
    
    if market_status != "CONNECTED":
        print("2. Refresh Market Data Connection:")
        print("   ./go_live.sh")
    
    if not strategies_ok:
        print("3. Check Strategy Configuration:")
        print("   Review configs/kite_day1_live.yaml")
    
    print("\n✅ Diagnostic Complete")

if __name__ == "__main__":
    main()




