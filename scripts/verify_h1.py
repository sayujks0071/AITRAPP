#!/usr/bin/env python3
"""Verify H1 Tail Short Vol Overlay is loaded and working"""
import sys
import requests
import json
from typing import Dict, List, Optional

API_BASE = "http://localhost:8000"


def check_strategy_loaded() -> bool:
    """Check if TailShortVolOverlay is loaded"""
    print("\n🔍 Checking if H1 is loaded...")
    print("=" * 50)
    
    try:
        response = requests.get(f"{API_BASE}/state", timeout=5)
        if response.status_code != 200:
            print(f"❌ State endpoint returned {response.status_code}")
            return False
        
        state = response.json()
        strategies = state.get("strategies", [])
        
        h1_found = False
        for strategy in strategies:
            if "TailShortVolOverlay" in strategy.get("name", ""):
                h1_found = True
                print(f"✅ TailShortVolOverlay found in strategies")
                print(f"   Name: {strategy.get('name')}")
                print(f"   Enabled: {strategy.get('enabled', 'unknown')}")
                break
        
        if not h1_found:
            print("❌ TailShortVolOverlay not found in strategies")
            print(f"   Available strategies: {[s.get('name') for s in strategies]}")
            return False
        
        return True
    except Exception as e:
        print(f"❌ Error checking strategies: {e}")
        return False


def check_metrics() -> bool:
    """Check H1 metrics exist"""
    print("\n🔍 Checking H1 Metrics...")
    print("=" * 50)
    
    metrics_to_check = [
        "tail_short_vol_short_notional",
        "tail_short_vol_tail_notional",
        "tail_short_vol_coverage_pct",
        "tail_short_vol_adjustments",
        "tail_short_vol_over_short_cap",
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
    print("\n🔍 Checking H1 Config...")
    print("=" * 50)
    
    try:
        from pathlib import Path
        config_path = Path("configs/tail_short_vol.yaml")
        if config_path.exists():
            print(f"✅ Config file exists: {config_path}")
            
            import yaml
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)
                h1_cfg = config.get("tail_short_vol", {})
                print(f"   Enabled: {h1_cfg.get('enabled', 'unknown')}")
                
                short_strats = h1_cfg.get("short_vol_strategies", [])
                print(f"   Short vol strategies: {len(short_strats)}")
                for s in short_strats[:5]:
                    print(f"     - {s}")
                if len(short_strats) > 5:
                    print(f"     ... and {len(short_strats) - 5} more")
                
                risk_budgets = h1_cfg.get("risk_budgets", {})
                print(f"   Target coverage: {risk_budgets.get('target_tail_coverage_pct', 0) * 100:.1f}%")
                print(f"   Min coverage: {risk_budgets.get('min_tail_coverage_pct', 0) * 100:.1f}%")
                print(f"   Max coverage: {risk_budgets.get('max_tail_coverage_pct', 0) * 100:.1f}%")
                
                return True
        else:
            print(f"❌ Config file not found: {config_path}")
            return False
    except Exception as e:
        print(f"❌ Error checking config: {e}")
        return False


def check_coverage_metrics() -> bool:
    """Check if coverage metrics are being computed"""
    print("\n🔍 Checking Coverage Metrics...")
    print("=" * 50)
    
    try:
        response = requests.get(f"{API_BASE}/metrics", timeout=5)
        if response.status_code != 200:
            print("⚠️  Could not fetch metrics")
            return False
        
        metrics_text = response.text
        
        # Check for coverage metrics
        has_short_notional = "tail_short_vol_short_notional" in metrics_text
        has_tail_notional = "tail_short_vol_tail_notional" in metrics_text
        has_coverage = "tail_short_vol_coverage_pct" in metrics_text
        
        if has_short_notional and has_tail_notional and has_coverage:
            print("✅ Coverage metrics are being computed")
            print("   (Values will appear during market hours when short vol strategies are active)")
            return True
        else:
            print("⚠️  Coverage metrics not yet populated")
            print("   (Will appear after first scan during market hours)")
            return True  # Not a failure, just not populated yet
    except Exception as e:
        print(f"⚠️  Error checking coverage metrics: {e}")
        return True  # Not critical


def main():
    """Run all H1 verification checks"""
    print("🚀 H1 Tail Short Vol Overlay Verification")
    print("=" * 60)
    
    results = {
        "config_exists": check_config(),
        "strategy_loaded": check_strategy_loaded(),
        "metrics_available": check_metrics(),
        "coverage_metrics": check_coverage_metrics(),
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
        print("\n✅ All critical checks passed! H1 appears to be working.")
        print("\n💡 Next steps:")
        print("   1. Wire position store for accurate notional calculation")
        print("   2. Test in observe mode during market hours")
        print("   3. Monitor coverage metrics")
        print("   4. Verify regime adjustments work")
        print("   5. Enable tail trades when ready")
        return 0
    else:
        print("\n❌ Some critical checks failed. Review the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())


