#!/usr/bin/env python3
"""
Comprehensive Trading System Diagnostic Tool

Analyzes the entire trading system to identify why trades aren't executing.
"""

import sys
import os
from pathlib import Path
import json
import re
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    print("⚠️  requests not available - API checks will be skipped")

def check_config_files():
    """Check all config files for dry_run setting"""
    print("\n" + "="*80)
    print("1. CONFIGURATION FILES CHECK")
    print("="*80)
    
    config_dir = project_root / "configs"
    issues = []
    
    live_configs = [
        "kite_day1_live.yaml",
        "kite_live.yaml", 
        "kite_canary_live.yaml",
        "mcx_live.yaml"
    ]
    
    for config_name in live_configs:
        config_path = config_dir / config_name
        if config_path.exists():
            with open(config_path) as f:
                content = f.read()
                has_dry_run = "dry_run" in content
                dry_run_false = "dry_run: false" in content or "dry_run: False" in content
                dry_run_true = "dry_run: true" in content or "dry_run: True" in content
                
                print(f"\n   {config_name}:")
                if dry_run_true:
                    print(f"      ❌ CRITICAL: dry_run is TRUE - trades will NOT execute!")
                    issues.append(f"{config_name}: dry_run is TRUE")
                elif dry_run_false:
                    print(f"      ✅ dry_run: false (correct)")
                elif has_dry_run:
                    print(f"      ⚠️  dry_run found but value unclear")
                else:
                    print(f"      ⚠️  dry_run not explicitly set (defaults to False)")
    
    return issues

def check_system_api():
    """Check system state via API"""
    print("\n" + "="*80)
    print("2. SYSTEM STATE (API CHECK)")
    print("="*80)
    
    if not HAS_REQUESTS:
        print("   ⚠️  Skipped (requests not available)")
        return {}
    
    try:
        resp = requests.get("http://localhost:8000/control/state", timeout=2)
        if resp.status_code == 200:
            state = resp.json()
            print("   ✅ API is accessible")
            print(f"   Paused: {state.get('is_paused', 'unknown')}")
            print(f"   Market Open: {state.get('is_market_open', 'unknown')}")
            print(f"   Trades Today: {state.get('trades_today', 0)}")
            print(f"   Positions: {state.get('num_positions', 0)}")
            return state
        else:
            print(f"   ⚠️  API returned status {resp.status_code}")
    except requests.exceptions.ConnectionError:
        print("   ⚠️  API not accessible (system may not be running)")
    except Exception as e:
        print(f"   ⚠️  API check failed: {e}")
    
    return {}

def analyze_logs():
    """Analyze log file for key indicators"""
    print("\n" + "="*80)
    print("3. LOG FILE ANALYSIS")
    print("="*80)
    
    log_path = project_root / "logs" / "aitrapp.log"
    
    if not log_path.exists():
        print("   ⚠️  Log file not found")
        return {}
    
    print(f"   Analyzing: {log_path}")
    
    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
        # Read last 10000 lines for analysis
        lines = f.readlines()
        if len(lines) > 10000:
            content = ''.join(lines[-10000:])
        else:
            content = ''.join(lines)
    
    # Count key patterns
    patterns = {
        "dry_run_mentions": r"DRY_RUN|dry_run",
        "scan_cycles": r"Running scan cycle",
        "signals_generated": r"Generated \d+ signals",
        "signals_rejected": r"Signal rejected|Risk check failed",
        "executions": r"Executing signal",
        "empty_universe": r"Universe is empty",
        "kill_switch": r"kill switch|Kill switch|KILL_SWITCH",
        "paused": r"is_paused.*true|PAUSED|paused",
        "orchestrator_started": r"Starting Trading Orchestrator|Main trading loop started",
        "universe_sync": r"universe.*sync|build.*universe",
    }
    
    counts = {}
    for key, pattern in patterns.items():
        matches = len(re.findall(pattern, content, re.IGNORECASE))
        counts[key] = matches
    
    print(f"\n   Key Metrics:")
    print(f"   - Orchestrator started: {counts.get('orchestrator_started', 0)} mentions")
    print(f"   - Scan cycles: {counts.get('scan_cycles', 0)}")
    print(f"   - Signals generated: {counts.get('signals_generated', 0)}")
    print(f"   - Signals rejected: {counts.get('signals_rejected', 0)}")
    print(f"   - Executions: {counts.get('executions', 0)}")
    print(f"   - DRY_RUN mentions: {counts.get('dry_run_mentions', 0)}")
    print(f"   - Empty universe warnings: {counts.get('empty_universe', 0)}")
    print(f"   - Kill switch mentions: {counts.get('kill_switch', 0)}")
    print(f"   - Paused mentions: {counts.get('paused', 0)}")
    print(f"   - Universe sync: {counts.get('universe_sync', 0)} mentions")
    
    # Find recent DRY_RUN messages
    if counts.get('dry_run_mentions', 0) > 0:
        print(f"\n   ⚠️  DRY_RUN detected! Recent messages:")
        dry_run_lines = [line for line in lines[-500:] if "DRY_RUN" in line.upper()]
        for line in dry_run_lines[-5:]:
            print(f"      {line.strip()[:100]}")
    
    # Find recent rejections
    if counts.get('signals_rejected', 0) > 0:
        print(f"\n   Recent rejections (last 5):")
        rejection_lines = [line for line in lines[-1000:] if "rejected" in line.lower() or "Risk check failed" in line]
        for line in rejection_lines[-5:]:
            # Try to extract JSON if present
            if '{' in line:
                try:
                    json_part = line[line.index('{'):]
                    data = json.loads(json_part)
                    reasons = data.get('reasons', [])
                    if reasons:
                        print(f"      Reason: {reasons[0]}")
                except:
                    print(f"      {line.strip()[:150]}")
            else:
                print(f"      {line.strip()[:150]}")
    
    return counts

def diagnose_issues(config_issues, state, log_counts):
    """Diagnose issues based on all checks"""
    print("\n" + "="*80)
    print("4. DIAGNOSIS")
    print("="*80)
    
    issues = []
    warnings = []
    
    # Config issues
    if config_issues:
        for issue in config_issues:
            issues.append(f"❌ {issue}")
    
    # System state
    if state:
        if state.get('is_paused'):
            issues.append("❌ System is PAUSED - no trades will execute")
        if state.get('trades_today', 0) == 0 and log_counts.get('executions', 0) == 0:
            warnings.append("⚠️  No trades executed today")
    
    # Log analysis
    if log_counts.get('orchestrator_started', 0) == 0:
        issues.append("❌ Orchestrator may not have started - check startup logs")
    
    if log_counts.get('scan_cycles', 0) == 0:
        issues.append("❌ No scan cycles detected - orchestrator may not be running")
    
    if log_counts.get('signals_generated', 0) == 0:
        issues.append("❌ No signals generated - check:")
        issues.append("     • Are strategies enabled?")
        issues.append("     • Is market data streaming?")
        issues.append("     • Are entry windows correct?")
    
    if log_counts.get('signals_rejected', 0) > log_counts.get('executions', 0) * 3:
        warnings.append("⚠️  Many signals rejected - check risk manager settings")
        warnings.append("     • Daily loss limit")
        warnings.append("     • Portfolio heat limit")
        warnings.append("     • Position sizing")
    
    if log_counts.get('empty_universe', 0) > 0:
        issues.append("❌ Universe is empty - check instrument sync")
    
    if log_counts.get('dry_run_mentions', 0) > 0:
        issues.append("❌ DRY_RUN mode detected in logs - trades are NOT executing!")
    
    if log_counts.get('kill_switch', 0) > 0:
        warnings.append("⚠️  Kill switch mentions found - check if active")
    
    if log_counts.get('paused', 0) > 10:
        warnings.append("⚠️  Many 'paused' mentions in logs - system may be paused")
    
    # Print issues
    if issues:
        print("\n   CRITICAL ISSUES:")
        for issue in issues:
            print(f"   {issue}")
    
    if warnings:
        print("\n   WARNINGS:")
        for warning in warnings:
            print(f"   {warning}")
    
    if not issues and not warnings:
        print("\n   ✅ No obvious blocking issues found")
        print("   If trades still aren't executing, check:")
        print("     • Market hours (system only trades during market hours)")
        print("     • Strategy-specific filters")
        print("     • Real-time log monitoring")
    
    return issues, warnings

def print_recommendations(issues, warnings):
    """Print recommended actions"""
    print("\n" + "="*80)
    print("5. RECOMMENDED ACTIONS")
    print("="*80)
    
    if not issues and not warnings:
        print("\n   System appears healthy. Monitor logs in real-time:")
        print("   tail -f logs/aitrapp.log | jq")
        return
    
    print("\n   Immediate Actions:")
    
    if any("dry_run" in str(i).lower() for i in issues):
        print("\n   1. Fix DRY_RUN mode:")
        print("      • Ensure all live configs have: dry_run: false")
        print("      • Restart the system")
    
    if any("paused" in str(i).lower() for i in issues):
        print("\n   2. Resume trading:")
        print("      curl -X POST http://localhost:8000/resume")
    
    if any("orchestrator" in str(i).lower() for i in issues):
        print("\n   3. Check orchestrator startup:")
        print("      grep 'Starting Trading Orchestrator' logs/aitrapp.log")
        print("      grep 'Main trading loop started' logs/aitrapp.log")
    
    if any("signals" in str(i).lower() and "generated" in str(i).lower() for i in issues):
        print("\n   4. Check signal generation:")
        print("      • Verify strategies are enabled in config")
        print("      • Check market data: grep 'Market data' logs/aitrapp.log")
        print("      • Check entry windows in config")
    
    if any("universe" in str(i).lower() for i in issues):
        print("\n   5. Fix universe:")
        print("      • Check instrument sync on startup")
        print("      • Verify universe config in YAML")
    
    print("\n   Monitoring Commands:")
    print("   • Real-time logs: tail -f logs/aitrapp.log | jq")
    print("   • System state: curl http://localhost:8000/control/state | jq")
    print("   • Check executions: grep 'Executing signal' logs/aitrapp.log | tail -20")
    print("   • Check rejections: grep 'Signal rejected' logs/aitrapp.log | tail -20")

def main():
    print("="*80)
    print("COMPREHENSIVE TRADING SYSTEM DIAGNOSTIC")
    print("="*80)
    print(f"Analysis time: {datetime.now().isoformat()}")
    print(f"Project root: {project_root}")
    
    # Run all checks
    config_issues = check_config_files()
    state = check_system_api()
    log_counts = analyze_logs()
    
    # Diagnose
    issues, warnings = diagnose_issues(config_issues, state, log_counts)
    
    # Recommendations
    print_recommendations(issues, warnings)
    
    print("\n" + "="*80)
    print("Analysis complete!")
    print("="*80)

if __name__ == "__main__":
    main()
