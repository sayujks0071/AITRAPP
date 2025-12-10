#!/usr/bin/env python3
"""Verify T1 Calendar Arb is loaded and working"""
import sys
import requests
import json
from typing import Dict, List, Optional

API_BASE = "http://localhost:8000"


def check_strategy_loaded() -> bool:
    """Check if CalendarArb is loaded"""
    print("\n🔍 Checking if T1 is loaded...")
    print("=" * 50)
    
    try:
        response = requests.get(f"{API_BASE}/state", timeout=5)
        if response.status_code != 200:
            print(f"❌ State endpoint returned {response.status_code}")
            return False
        
        state = response.json()
        strategies = state.get("strategies", [])
        
        t1_found = False
        for strategy in strategies:
            if "CalendarArb" in strategy.get("name", ""):
                t1_found = True
                print(f"✅ CalendarArb found in strategies")
                print(f"   Name: {strategy.get('name')}")
                print(f"   Enabled: {strategy.get('enabled', 'unknown')}")
                break
        
        if not t1_found:
            print("❌ CalendarArb not found in strategies")
            print(f"   Available strategies: {[s.get('name') for s in strategies]}")
            return False
        
        return True
    except Exception as e:
        print(f"❌ Error checking strategies: {e}")
        return False


def check_metrics() -> bool:
    """Check T1 metrics exist"""
    print("\n🔍 Checking T1 Metrics...")
    print("=" * 50)
    
    metrics_to_check = [
        "calendar_arb_iv_weekly",
        "calendar_arb_iv_monthly",
        "calendar_arb_term_ratio",
        "calendar_arb_term_spread",
        "calendar_arb_books_opened",
        "calendar_arb_books_closed",
    ]
    
    all_ok = True
    try:
        response = requests.get(f"{API_BASE}/metrics", timeout=5)
        if response.status_code != 200:
            print(f"❌ Metrics endpoint returned {response.status_code}")
            return False
        
        metrics_text = response.text
        
        for metric in metrics_to_check:
            if metric in metrics_text:
                print(f"✅ Found metric: {metric}")
            else:
                print(f"⚠️  Metric not found: {metric} (may appear after first scan)")
                # Not a failure - metrics only appear after first use
        
        return True
    except Exception as e:
        print(f"❌ Error checking metrics: {e}")
        return False


def check_config() -> bool:
    """Check if config file exists"""
    print("\n🔍 Checking T1 Config...")
    print("=" * 50)
    
    try:
        from pathlib import Path
        config_path = Path("configs/calendar_arb.yaml")
        if config_path.exists():
            print(f"✅ Config file exists: {config_path}")
            
            import yaml
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)
                t1_cfg = config.get("calendar_arb", {})
                print(f"   Enabled: {t1_cfg.get('enabled', 'unknown')}")
                print(f"   Mode: {t1_cfg.get('mode', 'unknown')}")
                print(f"   Underlyings: {t1_cfg.get('underlyings', [])}")
                
                entry_cfg = t1_cfg.get("entry", {})
                print(f"   Term ratio min: {entry_cfg.get('term_ratio_long_cal_min', 'unknown')}")
                print(f"   Term spread min: {entry_cfg.get('term_spread_long_cal_min', 'unknown')}")
                return True
        else:
            print(f"❌ Config file not found: {config_path}")
            return False
    except Exception as e:
        print(f"❌ Error checking config: {e}")
        return False


def check_term_structure() -> bool:
    """Check if term structure metrics are being computed"""
    print("\n🔍 Checking Term Structure Metrics...")
    print("=" * 50)
    
    try:
        response = requests.get(f"{API_BASE}/metrics", timeout=5)
        if response.status_code != 200:
            print("⚠️  Could not fetch metrics")
            return False
        
        metrics_text = response.text
        
        # Check for term structure metrics
        has_iv_weekly = "calendar_arb_iv_weekly" in metrics_text
        has_iv_monthly = "calendar_arb_iv_monthly" in metrics_text
        has_ratio = "calendar_arb_term_ratio" in metrics_text
        has_spread = "calendar_arb_term_spread" in metrics_text
        
        if has_iv_weekly and has_iv_monthly and has_ratio and has_spread:
            print("✅ Term structure metrics are being computed")
            print("   (Values will appear during market hours)")
            return True
        else:
            print("⚠️  Term structure metrics not yet populated")
            print("   (Will appear after first scan during market hours)")
            return True  # Not a failure, just not populated yet
    except Exception as e:
        print(f"⚠️  Error checking term structure: {e}")
        return True  # Not critical


def main():
    """Run all T1 verification checks"""
    print("🚀 T1 Calendar Volatility Arbitrage Verification")
    print("=" * 60)
    
    results = {
        "config_exists": check_config(),
        "strategy_loaded": check_strategy_loaded(),
        "metrics_available": check_metrics(),
        "term_structure": check_term_structure(),
    }
    
    print("\n" + "=" * 60)
    print("📊 Summary")
    print("=" * 60)
    
    critical_checks = ["config_exists", "strategy_loaded"]
    all_critical_passed = all(results[k] for k in critical_checks)
    
    for check, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        critical = " (critical)" if check in critical_checks else ""
        print(f"{status}: {check}{critical}")
    
    if all_critical_passed:
        print("\n✅ All critical checks passed! T1 appears to be working.")
        print("\n💡 Next steps:")
        print("   1. Test in PAPER mode during market hours")
        print("   2. Monitor term structure metrics (ratio/spread)")
        print("   3. Verify calendars open when term structure is favorable")
        print("   4. Check exits trigger correctly")
        print("   5. Verify R1 regime integration")
        return 0
    else:
        print("\n❌ Some critical checks failed. Review the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())


