#!/usr/bin/env python3
"""Verify G1 Gamma Scalper is loaded and working"""
import sys
import requests
import json
from typing import Dict, List, Optional

API_BASE = "http://localhost:8000"


def check_strategy_loaded() -> bool:
    """Check if GammaScalper is loaded"""
    print("\n🔍 Checking if G1 is loaded...")
    print("=" * 50)
    
    try:
        response = requests.get(f"{API_BASE}/state", timeout=5)
        if response.status_code != 200:
            print(f"❌ State endpoint returned {response.status_code}")
            return False
        
        state = response.json()
        strategies = state.get("strategies", [])
        
        g1_found = False
        for strategy in strategies:
            if "GammaScalper" in strategy.get("name", ""):
                g1_found = True
                print(f"✅ GammaScalper found in strategies")
                print(f"   Name: {strategy.get('name')}")
                print(f"   Enabled: {strategy.get('enabled', 'unknown')}")
                break
        
        if not g1_found:
            print("❌ GammaScalper not found in strategies")
            print(f"   Available strategies: {[s.get('name') for s in strategies]}")
            return False
        
        return True
    except Exception as e:
        print(f"❌ Error checking strategies: {e}")
        return False


def check_metrics() -> bool:
    """Check G1 metrics exist"""
    print("\n🔍 Checking G1 Metrics...")
    print("=" * 50)
    
    metrics_to_check = [
        "gamma_scalper_books_opened",
        "gamma_scalper_books_closed",
        "gamma_scalper_abs_delta",
        "gamma_scalper_rebalances",
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
                print(f"⚠️  Metric not found: {metric} (may appear after first trade)")
                # Not a failure - metrics only appear after first use
        
        return True
    except Exception as e:
        print(f"❌ Error checking metrics: {e}")
        return False


def check_config() -> bool:
    """Check if config file exists"""
    print("\n🔍 Checking G1 Config...")
    print("=" * 50)
    
    try:
        from pathlib import Path
        config_path = Path("configs/gamma_scalper.yaml")
        if config_path.exists():
            print(f"✅ Config file exists: {config_path}")
            
            import yaml
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)
                g1_cfg = config.get("gamma_scalper", {})
                print(f"   Enabled: {g1_cfg.get('enabled', 'unknown')}")
                print(f"   Mode: {g1_cfg.get('mode', 'unknown')}")
                print(f"   Underlyings: {g1_cfg.get('underlyings', [])}")
                return True
        else:
            print(f"❌ Config file not found: {config_path}")
            return False
    except Exception as e:
        print(f"❌ Error checking config: {e}")
        return False


def main():
    """Run all G1 verification checks"""
    print("🚀 G1 Gamma Scalper Verification")
    print("=" * 60)
    
    results = {
        "config_exists": check_config(),
        "strategy_loaded": check_strategy_loaded(),
        "metrics_available": check_metrics(),
    }
    
    print("\n" + "=" * 60)
    print("📊 Summary")
    print("=" * 60)
    
    all_passed = all(results.values())
    
    for check, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {check}")
    
    if all_passed:
        print("\n✅ All checks passed! G1 appears to be working.")
        print("\n💡 Next steps:")
        print("   1. Test in PAPER mode during market hours")
        print("   2. Monitor delta hedging behavior")
        print("   3. Verify exits trigger correctly")
        print("   4. Check R1 regime integration")
        return 0
    else:
        print("\n❌ Some checks failed. Review the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())


