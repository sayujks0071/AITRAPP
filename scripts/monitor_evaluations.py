#!/usr/bin/env python3
"""
Monitor Strategy Evaluations - See What the System is Thinking
================================================================
Monitors API endpoints and logs to show strategy evaluation activity.
"""
import requests
import time
import json
from datetime import datetime
from pathlib import Path

API_BASE = "http://localhost:8000"

def check_strategy_activity():
    """Check for strategy evaluation activity via API"""
    try:
        # Check execution stats
        resp = requests.get(f"{API_BASE}/api/execution/stats", timeout=2)
        if resp.status_code == 200:
            stats = resp.json()
            attempts = stats.get("attempts", 0)
            if attempts > 0:
                print(f"✅ Execution attempts: {attempts}")
                return True
        
        # Check positions
        resp = requests.get(f"{API_BASE}/positions", timeout=2)
        if resp.status_code == 200:
            positions = resp.json()
            if positions:
                print(f"✅ Active positions: {len(positions)}")
                return True
        
        return False
    except:
        return False

def monitor_logs():
    """Monitor log files for evaluation messages"""
    log_paths = [
        "/tmp/aitrapp.log",
        "logs/trading.log",
        "logs/aitrapp_crypto.log",
        "logs/aitrapp.log"
    ]
    
    for log_path in log_paths:
        path = Path(log_path)
        if path.exists():
            print(f"📁 Monitoring: {log_path}")
            return log_path
    
    return None

def main():
    print("="*80)
    print("🔍 STRATEGY EVALUATION MONITOR")
    print("="*80)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\nMonitoring for strategy evaluation activity...")
    print("Press Ctrl+C to stop\n")
    
    log_file = monitor_logs()
    
    if log_file:
        print(f"✅ Found log file: {log_file}")
        print(f"\n📊 To monitor in real-time, run:")
        print(f"   tail -f {log_file} | grep -i 'Evaluating\\|Skipping\\|Entry\\|Regime'")
    else:
        print("⚠️  No log files found in standard locations")
        print("\n💡 Logs may be going to stdout (check terminal where go_live.sh is running)")
        print("   Or logs may not be configured to write to files")
    
    print("\n" + "="*80)
    print("📋 ALTERNATIVE MONITORING METHODS")
    print("="*80)
    print("\n1. Check API endpoints:")
    print("   curl http://localhost:8000/api/execution/stats")
    print("   curl http://localhost:8000/positions")
    print("   curl http://localhost:8000/api/strategies/summary")
    
    print("\n2. Monitor stdout (if go_live.sh is in foreground):")
    print("   # Check the terminal where ./go_live.sh was started")
    
    print("\n3. Force a scan to trigger evaluations:")
    print("   curl -X POST http://localhost:8000/debug/scan-once")
    
    print("\n4. Check regime status:")
    print("   curl http://localhost:8000/api/regime/current")
    
    print("\n" + "="*80)
    
    # Check current activity
    print("\n🔍 Current System Activity:")
    print("-" * 80)
    if check_strategy_activity():
        print("✅ System is active")
    else:
        print("⚠️  No execution activity detected")
        print("   → Strategies may be evaluating but not executing")
        print("   → Check regime and filter status")

if __name__ == "__main__":
    main()




