#!/usr/bin/env python3
"""Dry run of PAPER playbook - Rehearse operational procedures"""
import sys
import requests
import json
from datetime import datetime
from pathlib import Path

API_BASE = "http://localhost:8000"


def check_health():
    """Check system health"""
    print("🔍 Pre-Open Checklist")
    print("=" * 60)
    print()
    
    checks = {
        "Health endpoint": False,
        "State endpoint": False,
        "Ready endpoint": False,
        "Metrics endpoint": False,
    }
    
    try:
        # Health check
        response = requests.get(f"{API_BASE}/health", timeout=5)
        if response.status_code == 200:
            checks["Health endpoint"] = True
            print("✅ /health - OK")
        else:
            print(f"❌ /health - Status {response.status_code}")
    except Exception as e:
        print(f"❌ /health - Error: {e}")
    
    try:
        # State check
        response = requests.get(f"{API_BASE}/state", timeout=5)
        if response.status_code == 200:
            checks["State endpoint"] = True
            state = response.json()
            mode = state.get("mode", "UNKNOWN")
            print(f"✅ /state - OK (mode: {mode})")
        else:
            print(f"❌ /state - Status {response.status_code}")
    except Exception as e:
        print(f"❌ /state - Error: {e}")
    
    try:
        # Ready check
        response = requests.get(f"{API_BASE}/ready", timeout=5)
        if response.status_code == 200:
            checks["Ready endpoint"] = True
            ready_data = response.json()
            ready = ready_data.get("ready", False)
            leader = ready_data.get("leader", 0)
            print(f"✅ /ready - OK (ready: {ready}, leader: {leader})")
        else:
            print(f"❌ /ready - Status {response.status_code}")
    except Exception as e:
        print(f"❌ /ready - Error: {e}")
    
    try:
        # Metrics check
        response = requests.get(f"{API_BASE}/metrics", timeout=5)
        if response.status_code == 200:
            checks["Metrics endpoint"] = True
            metrics_text = response.text
            # Check for key metrics
            has_regime = "algo_vol_regime_code" in metrics_text
            has_allocator = "allocator_max_capital_pct" in metrics_text
            has_tail = "tail_short_vol_coverage_pct" in metrics_text
            print(f"✅ /metrics - OK (regime: {has_regime}, allocator: {has_allocator}, tail: {has_tail})")
        else:
            print(f"❌ /metrics - Status {response.status_code}")
    except Exception as e:
        print(f"❌ /metrics - Error: {e}")
    
    print()
    all_passed = all(checks.values())
    return all_passed


def run_verifications():
    """Run all verification scripts"""
    print("🔍 Strategy Verifications")
    print("=" * 60)
    print()
    
    verifications = [
        ("R1", "scripts/verify_r1.py"),
        ("G1", "scripts/verify_g1.py"),
        ("T1", "scripts/verify_t1.py"),
        ("D1", "scripts/verify_d1.py"),
        ("H1", "scripts/verify_h1.py"),
        ("Allocator", "scripts/verify_allocator.py"),
    ]
    
    results = {}
    for name, script_path in verifications:
        print(f"Running {name} verification...")
        try:
            import subprocess
            result = subprocess.run(
                ["python3", script_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                results[name] = True
                print(f"✅ {name} - PASSED")
            else:
                results[name] = False
                print(f"⚠️  {name} - FAILED (check output)")
        except Exception as e:
            results[name] = False
            print(f"❌ {name} - Error: {e}")
        print()
    
    all_passed = all(results.values())
    return all_passed, results


def check_metrics():
    """Check key metrics are accessible"""
    print("📊 During Market - Key Metrics")
    print("=" * 60)
    print()
    
    try:
        response = requests.get(f"{API_BASE}/metrics", timeout=5)
        if response.status_code != 200:
            print("❌ Could not fetch metrics")
            return False
        
        metrics_text = response.text
        
        metric_checks = {
            "Regime (R1)": [
                "algo_vol_regime_code",
                "algo_vol_iv_rank",
                "algo_vol_atr_pct",
            ],
            "Gamma Scalper (G1)": [
                "gamma_scalper_books_opened",
                "gamma_scalper_abs_delta",
                "gamma_scalper_pnl_pct",
            ],
            "Calendar Arb (T1)": [
                "calendar_arb_term_ratio",
                "calendar_arb_books_opened",
                "calendar_arb_pnl_pct",
            ],
            "Dispersion Arb (D1)": [
                "dispersion_arb_vol_ratio",
                "dispersion_arb_corr",
                "dispersion_arb_pnl_pct",
            ],
            "Allocator": [
                "allocator_final_weight",
                "allocator_max_capital_pct",
                "allocator_enabled",
            ],
            "Tail Overlay (H1)": [
                "tail_short_vol_short_notional",
                "tail_short_vol_tail_notional",
                "tail_short_vol_coverage_pct",
            ],
        }
        
        all_found = True
        for category, metrics in metric_checks.items():
            found = [m for m in metrics if m in metrics_text]
            if found:
                print(f"✅ {category}: {len(found)}/{len(metrics)} metrics found")
            else:
                print(f"⚠️  {category}: No metrics found (may appear after first use)")
                all_found = False
        
        print()
        return True
    except Exception as e:
        print(f"❌ Error checking metrics: {e}")
        return False


def generate_daily_report():
    """Generate and review daily report"""
    print("🧾 Post-Close - Daily Report")
    print("=" * 60)
    print()
    
    try:
        import subprocess
        result = subprocess.run(
            ["python3", "scripts/generate_daily_report.py"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print("✅ Daily report generated successfully")
            print()
            print("Report output:")
            print("-" * 60)
            print(result.stdout)
            
            # Check if report file was created
            report_dir = Path("reports/daily")
            if report_dir.exists():
                json_files = list(report_dir.glob("*_report.json"))
                md_files = list(report_dir.glob("*_report.md"))
                if json_files or md_files:
                    print()
                    print("Report files created:")
                    for f in json_files[-1:]:  # Show latest
                        print(f"  📄 {f}")
                    for f in md_files[-1:]:  # Show latest
                        print(f"  📄 {f}")
            
            return True
        else:
            print("❌ Daily report generation failed")
            print(result.stderr)
            return False
    except Exception as e:
        print(f"❌ Error generating report: {e}")
        return False


def main():
    """Run dry run of PAPER playbook"""
    print("🚀 PAPER Playbook Dry Run")
    print("=" * 60)
    print()
    print("This is a rehearsal - no markets needed")
    print("Goal: Verify all procedures work")
    print()
    
    results = {
        "pre_open": False,
        "verifications": False,
        "metrics": False,
        "daily_report": False,
    }
    
    # Pre-open checklist
    results["pre_open"] = check_health()
    print()
    
    # Run verifications
    verif_passed, verif_results = run_verifications()
    results["verifications"] = verif_passed
    print()
    
    # Check metrics
    results["metrics"] = check_metrics()
    print()
    
    # Generate daily report
    results["daily_report"] = generate_daily_report()
    print()
    
    # Summary
    print("=" * 60)
    print("📊 Dry Run Summary")
    print("=" * 60)
    print()
    
    for check, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {check}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print()
        print("✅ All procedures working!")
        print()
        print("💡 You're ready to run the PAPER playbook for real.")
        print("   Follow docs/PAPER_PLAYBOOK.md during market hours.")
        return 0
    else:
        print()
        print("❌ Some procedures need attention.")
        print("   Fix issues before running PAPER playbook.")
        return 1


if __name__ == "__main__":
    sys.exit(main())


