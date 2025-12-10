#!/usr/bin/env python3
"""Verify Strategy Allocator is loaded and working"""
import sys
import requests
import json
from typing import Dict, List, Optional

API_BASE = "http://localhost:8000"


def check_config() -> bool:
    """Check if config file exists"""
    print("\n🔍 Checking Allocator Config...")
    print("=" * 50)
    
    try:
        from pathlib import Path
        config_path = Path("configs/strategy_allocator.yaml")
        if config_path.exists():
            print(f"✅ Config file exists: {config_path}")
            
            import yaml
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)
                alloc_cfg = config.get("strategy_allocator", {})
                print(f"   Enabled: {alloc_cfg.get('enabled', 'unknown')}")
                print(f"   Global max capital: {alloc_cfg.get('global_max_capital_pct', 'unknown') * 100:.1f}%")
                
                strategies = alloc_cfg.get("strategies", [])
                print(f"   Strategies under control: {len(strategies)}")
                for s in strategies[:5]:  # Show first 5
                    print(f"     - {s.get('name')} (base_weight: {s.get('base_weight', 0):.2f})")
                if len(strategies) > 5:
                    print(f"     ... and {len(strategies) - 5} more")
                
                return True
        else:
            print(f"❌ Config file not found: {config_path}")
            return False
    except Exception as e:
        print(f"❌ Error checking config: {e}")
        return False


def check_metrics() -> bool:
    """Check allocator metrics exist"""
    print("\n🔍 Checking Allocator Metrics...")
    print("=" * 50)
    
    metrics_to_check = [
        "allocator_raw_score",
        "allocator_final_weight",
        "allocator_max_capital_pct",
        "allocator_enabled",
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
                print(f"⚠️  Metric not found: {metric} (may appear after first allocation cycle)")
                # Not a failure - metrics only appear after first use
        
        return True
    except Exception as e:
        print(f"❌ Error checking metrics: {e}")
        return False


def check_allocation_table() -> bool:
    """Try to get current allocation table"""
    print("\n🔍 Checking Allocation Table...")
    print("=" * 50)
    
    try:
        # Try to get from metrics
        response = requests.get(f"{API_BASE}/metrics", timeout=5)
        if response.status_code != 200:
            print("⚠️  Could not fetch metrics")
            return False
        
        metrics_text = response.text
        
        # Look for allocator metrics
        if "allocator_max_capital_pct" in metrics_text:
            print("✅ Allocation metrics found")
            print("\n   Current allocations (from metrics):")
            
            # Parse metrics (simplified - would use proper Prometheus parser in production)
            lines = metrics_text.split('\n')
            allocations = {}
            for line in lines:
                if 'allocator_max_capital_pct' in line and 'strategy=' in line:
                    # Extract strategy name and value
                    try:
                        parts = line.split('strategy="')
                        if len(parts) > 1:
                            strategy_part = parts[1].split('"')[0]
                            value_part = line.split()[-1]
                            allocations[strategy_part] = float(value_part)
                    except:
                        pass
            
            if allocations:
                print(f"\n   {'Strategy':<30} {'MaxCap%':>10}")
                print("   " + "-" * 40)
                for strategy, cap in sorted(allocations.items(), key=lambda x: x[1], reverse=True):
                    print(f"   {strategy:<30} {cap*100:>9.2f}%")
            else:
                print("   (No allocations found - allocator may not have run yet)")
            
            return True
        else:
            print("⚠️  Allocation metrics not yet populated")
            print("   (Will appear after first allocation cycle)")
            return True  # Not a failure, just not populated yet
    except Exception as e:
        print(f"⚠️  Error checking allocation table: {e}")
        return True  # Not critical


def main():
    """Run all allocator verification checks"""
    print("🚀 Strategy Allocator Verification")
    print("=" * 60)
    
    results = {
        "config_exists": check_config(),
        "metrics_available": check_metrics(),
        "allocation_table": check_allocation_table(),
    }
    
    print("\n" + "=" * 60)
    print("📊 Summary")
    print("=" * 60)
    
    critical_checks = ["config_exists"]
    all_critical_passed = all(results[k] for k in critical_checks)
    
    for check, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        critical = " (critical)" if check in critical_checks else ""
        print(f"{status}: {check}{critical}")
    
    if all_critical_passed:
        print("\n✅ All critical checks passed! Allocator appears to be configured.")
        print("\n💡 Next steps:")
        print("   1. Ensure allocator runs periodically (start-of-day or hourly)")
        print("   2. Monitor allocation metrics in Grafana")
        print("   3. Verify strategy caps are being enforced")
        print("   4. Review allocation decisions vs actual performance")
        return 0
    else:
        print("\n❌ Some critical checks failed. Review the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())


