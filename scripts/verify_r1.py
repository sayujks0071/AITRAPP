#!/usr/bin/env python3
"""Verify R1 Regime-Switching Volatility Engine is loaded and working"""
import sys
import requests
import json
from typing import Dict, List, Optional

API_BASE = "http://localhost:8000"


def check_metrics(metric_name: str, expected_labels: Optional[List[str]] = None) -> bool:
    """Check if a metric exists in Prometheus"""
    try:
        response = requests.get(f"{API_BASE}/metrics", timeout=5)
        if response.status_code != 200:
            print(f"❌ Metrics endpoint returned {response.status_code}")
            return False
        
        metrics_text = response.text
        found = metric_name in metrics_text
        
        if found:
            print(f"✅ Found metric: {metric_name}")
            if expected_labels:
                # Check for expected label combinations
                for label in expected_labels:
                    if label in metrics_text:
                        print(f"   ✅ Found label: {label}")
                    else:
                        print(f"   ⚠️  Missing label: {label}")
            return True
        else:
            print(f"❌ Metric not found: {metric_name}")
            return False
    except Exception as e:
        print(f"❌ Error checking metrics: {e}")
        return False


def check_regime_metrics() -> bool:
    """Check all R1 regime metrics"""
    print("\n🔍 Checking R1 Regime Metrics...")
    print("=" * 50)
    
    all_ok = True
    
    # Core regime metrics
    metrics_to_check = [
        ("algo_vol_regime_code", ["underlying=\"NIFTY\"", "underlying=\"BANKNIFTY\""]),
        ("algo_vol_iv_rank", ["underlying=\"NIFTY\"", "underlying=\"BANKNIFTY\""]),
        ("algo_vol_atr_pct", ["underlying=\"NIFTY\"", "underlying=\"BANKNIFTY\""]),
        ("algo_vol_rv_iv_ratio", ["underlying=\"NIFTY\"", "underlying=\"BANKNIFTY\""]),
        ("algo_vol_vix_rank", ["underlying=\"NIFTY\"", "underlying=\"BANKNIFTY\""]),
    ]
    
    for metric, labels in metrics_to_check:
        if not check_metrics(metric, labels):
            all_ok = False
    
    # Check regime flags
    print("\n🔍 Checking regime flags...")
    regime_flags = [
        "algo_vol_regime_flag{underlying=\"NIFTY\",regime=\"LOW_MEAN_REVERT\"}",
        "algo_vol_regime_flag{underlying=\"NIFTY\",regime=\"MEDIUM_TREND\"}",
        "algo_vol_regime_flag{underlying=\"NIFTY\",regime=\"HIGH_EVENT\"}",
        "algo_vol_regime_flag{underlying=\"NIFTY\",regime=\"CHAOTIC\"}",
        "algo_vol_regime_flag{underlying=\"NIFTY\",regime=\"UNKNOWN\"}",
    ]
    
    try:
        response = requests.get(f"{API_BASE}/metrics", timeout=5)
        metrics_text = response.text
        for flag in regime_flags:
            if flag in metrics_text:
                print(f"✅ Found: {flag}")
            else:
                print(f"⚠️  Missing: {flag}")
    except Exception as e:
        print(f"❌ Error checking regime flags: {e}")
        all_ok = False
    
    return all_ok


def check_strategy_loaded() -> bool:
    """Check if RegimeVolEngine is loaded in strategies"""
    print("\n🔍 Checking if R1 is loaded...")
    print("=" * 50)
    
    try:
        response = requests.get(f"{API_BASE}/state", timeout=5)
        if response.status_code != 200:
            print(f"❌ State endpoint returned {response.status_code}")
            return False
        
        state = response.json()
        strategies = state.get("strategies", [])
        
        r1_found = False
        for strategy in strategies:
            if "RegimeVolEngine" in strategy.get("name", ""):
                r1_found = True
                print(f"✅ RegimeVolEngine found in strategies")
                print(f"   Name: {strategy.get('name')}")
                print(f"   Enabled: {strategy.get('enabled', 'unknown')}")
                break
        
        if not r1_found:
            print("❌ RegimeVolEngine not found in strategies")
            print(f"   Available strategies: {[s.get('name') for s in strategies]}")
            return False
        
        return True
    except Exception as e:
        print(f"❌ Error checking strategies: {e}")
        return False


def check_logs_for_r1() -> bool:
    """Check if R1 initialization appears in logs"""
    print("\n🔍 Checking logs for R1 initialization...")
    print("=" * 50)
    
    try:
        import subprocess
        result = subprocess.run(
            ["grep", "-i", "regime.*vol.*engine", "/tmp/kite_api_live.log"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0 and result.stdout:
            lines = result.stdout.strip().split('\n')
            print(f"✅ Found {len(lines)} log entries mentioning R1")
            for line in lines[-3:]:  # Show last 3
                print(f"   {line[:100]}...")
            return True
        else:
            print("⚠️  No R1 mentions in logs (may be normal if just started)")
            return True  # Not a failure, just informational
    except Exception as e:
        print(f"⚠️  Could not check logs: {e}")
        return True  # Not critical


def get_current_regimes() -> Dict[str, Optional[float]]:
    """Get current regime codes for each underlying"""
    print("\n🔍 Getting current regime codes...")
    print("=" * 50)
    
    regimes = {}
    try:
        response = requests.get(f"{API_BASE}/metrics", timeout=5)
        metrics_text = response.text
        
        for underlying in ["NIFTY", "BANKNIFTY"]:
            pattern = f'algo_vol_regime_code{{underlying="{underlying}"}}'
            for line in metrics_text.split('\n'):
                if pattern in line and not line.strip().startswith('#'):
                    try:
                        # Extract value (format: metric_name{labels} value)
                        parts = line.split()
                        if len(parts) >= 2:
                            value = float(parts[-1])
                            regimes[underlying] = value
                            regime_name = {
                                0: "UNKNOWN",
                                1: "LOW_MEAN_REVERT",
                                2: "MEDIUM_TREND",
                                3: "HIGH_EVENT",
                                4: "CHAOTIC"
                            }.get(int(value), "UNKNOWN")
                            print(f"✅ {underlying}: {regime_name} (code: {int(value)})")
                            break
                    except (ValueError, IndexError):
                        pass
        
        if not regimes:
            print("⚠️  No regime codes found (R1 may not have run yet)")
        
        return regimes
    except Exception as e:
        print(f"❌ Error getting regimes: {e}")
        return regimes


def main():
    """Run all R1 verification checks"""
    print("🚀 R1 Regime-Switching Volatility Engine Verification")
    print("=" * 60)
    
    results = {
        "strategy_loaded": check_strategy_loaded(),
        "regime_metrics": check_regime_metrics(),
        "logs_check": check_logs_for_r1(),
    }
    
    regimes = get_current_regimes()
    
    print("\n" + "=" * 60)
    print("📊 Summary")
    print("=" * 60)
    
    all_passed = all(results.values())
    
    for check, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {check}")
    
    if regimes:
        print(f"\n📈 Current Regimes:")
        for underlying, code in regimes.items():
            regime_name = {
                0: "UNKNOWN",
                1: "LOW_MEAN_REVERT",
                2: "MEDIUM_TREND",
                3: "HIGH_EVENT",
                4: "CHAOTIC"
            }.get(int(code), "UNKNOWN")
            print(f"   {underlying}: {regime_name}")
    
    if all_passed:
        print("\n✅ All checks passed! R1 appears to be working.")
        print("\n💡 Next steps:")
        print("   1. Monitor metrics during market hours")
        print("   2. Verify routing to A-G strategies")
        print("   3. Check entry_regime tagging on trades")
        return 0
    else:
        print("\n❌ Some checks failed. Review the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())


