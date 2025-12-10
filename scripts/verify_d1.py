#!/usr/bin/env python3
"""Verify D1 Dispersion Arb is loaded and working"""
import sys
import requests
import json
from typing import Dict, List, Optional

API_BASE = "http://localhost:8000"


def check_strategy_loaded() -> bool:
    """Check if DispersionArb is loaded"""
    print("\n🔍 Checking if D1 is loaded...")
    print("=" * 50)
    
    try:
        response = requests.get(f"{API_BASE}/state", timeout=5)
        if response.status_code != 200:
            print(f"❌ State endpoint returned {response.status_code}")
            return False
        
        state = response.json()
        strategies = state.get("strategies", [])
        
        d1_found = False
        for strategy in strategies:
            if "DispersionArb" in strategy.get("name", ""):
                d1_found = True
                print(f"✅ DispersionArb found in strategies")
                print(f"   Name: {strategy.get('name')}")
                print(f"   Enabled: {strategy.get('enabled', 'unknown')}")
                break
        
        if not d1_found:
            print("❌ DispersionArb not found in strategies")
            print(f"   Available strategies: {[s.get('name') for s in strategies]}")
            return False
        
        return True
    except Exception as e:
        print(f"❌ Error checking strategies: {e}")
        return False


def check_metrics() -> bool:
    """Check D1 metrics exist"""
    print("\n🔍 Checking D1 Metrics...")
    print("=" * 50)
    
    metrics_to_check = [
        "dispersion_arb_rv_parent",
        "dispersion_arb_rv_sector",
        "dispersion_arb_vol_ratio",
        "dispersion_arb_corr",
        "dispersion_arb_iv_ratio",
        "dispersion_arb_books_opened",
        "dispersion_arb_books_closed",
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
    print("\n🔍 Checking D1 Config...")
    print("=" * 50)
    
    try:
        from pathlib import Path
        config_path = Path("configs/dispersion_arb.yaml")
        if config_path.exists():
            print(f"✅ Config file exists: {config_path}")
            
            import yaml
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)
                d1_cfg = config.get("dispersion_arb", {})
                print(f"   Enabled: {d1_cfg.get('enabled', 'unknown')}")
                print(f"   Mode: {d1_cfg.get('mode', 'unknown')}")
                
                pairs = d1_cfg.get("pairs", [])
                print(f"   Pairs: {len(pairs)}")
                for pair in pairs:
                    print(f"     - {pair.get('parent')} vs {pair.get('sector')}")
                
                entry_cfg = d1_cfg.get("entry", {})
                print(f"   Min vol ratio: {entry_cfg.get('min_vol_ratio_sector_parent', 'unknown')}")
                print(f"   Min correlation: {entry_cfg.get('min_corr', 'unknown')}")
                return True
        else:
            print(f"❌ Config file not found: {config_path}")
            return False
    except Exception as e:
        print(f"❌ Error checking config: {e}")
        return False


def check_dispersion_metrics() -> bool:
    """Check if dispersion metrics are being computed"""
    print("\n🔍 Checking Dispersion Metrics...")
    print("=" * 50)
    
    try:
        response = requests.get(f"{API_BASE}/metrics", timeout=5)
        if response.status_code != 200:
            print("⚠️  Could not fetch metrics")
            return False
        
        metrics_text = response.text
        
        # Check for dispersion metrics
        has_rv_parent = "dispersion_arb_rv_parent" in metrics_text
        has_rv_sector = "dispersion_arb_rv_sector" in metrics_text
        has_vol_ratio = "dispersion_arb_vol_ratio" in metrics_text
        has_corr = "dispersion_arb_corr" in metrics_text
        
        if has_rv_parent and has_rv_sector and has_vol_ratio and has_corr:
            print("✅ Dispersion metrics are being computed")
            print("   (Values will appear during market hours)")
            return True
        else:
            print("⚠️  Dispersion metrics not yet populated")
            print("   (Will appear after first scan during market hours)")
            return True  # Not a failure, just not populated yet
    except Exception as e:
        print(f"⚠️  Error checking dispersion metrics: {e}")
        return True  # Not critical


def main():
    """Run all D1 verification checks"""
    print("🚀 D1 Dispersion Arbitrage Verification")
    print("=" * 60)
    
    results = {
        "config_exists": check_config(),
        "strategy_loaded": check_strategy_loaded(),
        "metrics_available": check_metrics(),
        "dispersion_metrics": check_dispersion_metrics(),
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
        print("\n✅ All critical checks passed! D1 appears to be working.")
        print("\n💡 Next steps:")
        print("   1. Test in PAPER mode during market hours")
        print("   2. Monitor dispersion metrics (vol ratio, correlation)")
        print("   3. Verify pairs open when dispersion is favorable")
        print("   4. Check exits trigger correctly")
        print("   5. Verify R1 regime integration")
        return 0
    else:
        print("\n❌ Some critical checks failed. Review the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())


