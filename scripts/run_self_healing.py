#!/usr/bin/env python3
"""
Self-Healing Diagnostic & Healing Script
=========================================

Runs diagnostics and applies healing actions if needed.

Usage:
    python3 scripts/run_self_healing.py [--dry-run] [--config-path configs/kite_day1_live.yaml]
"""

import sys
import argparse
import requests
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from packages.core.self_healing import SelfDiagnostics, SelfHealing, AnomalyType
from packages.core.rag_memory import RAGMemory
from packages.core.config import app_config, settings

API_BASE = "http://localhost:8000"


def fetch_state() -> dict:
    """Fetch system state from API"""
    try:
        response = requests.get(f"{API_BASE}/state", timeout=10)
        if response.status_code == 200:
            return response.json()
        return {}
    except Exception as e:
        print(f"⚠️  Could not fetch state: {e}")
        return {}


def fetch_execution_stats() -> dict:
    """Fetch execution stats from API"""
    try:
        response = requests.get(f"{API_BASE}/api/execution/stats", timeout=10)
        if response.status_code == 200:
            return response.json()
        return {}
    except Exception as e:
        print(f"⚠️  Could not fetch execution stats: {e}")
        return {}


def main():
    parser = argparse.ArgumentParser(description="Run self-healing diagnostics and apply fixes")
    parser.add_argument("--dry-run", action="store_true", help="Run diagnostics but don't apply healing")
    parser.add_argument("--config-path", type=str, default=None, help="Path to config YAML file")
    parser.add_argument("--memory-path", type=str, default="data/memory.json", help="Path to RAG memory file")
    
    args = parser.parse_args()
    
    # Determine config path
    if args.config_path:
        config_path = args.config_path
    elif settings.app_config_path:
        config_path = settings.app_config_path
    elif hasattr(app_config, 'config_path'):
        config_path = str(app_config.config_path)
    else:
        config_path = "configs/kite_day1_live.yaml"
    
    config_path = Path(config_path)
    
    if not config_path.exists():
        print(f"❌ Config file not found: {config_path}")
        sys.exit(1)
    
    print("=" * 60)
    print("🔍 SELF-HEALING DIAGNOSTICS & HEALING")
    print("=" * 60)
    print(f"📁 Config: {config_path}")
    print(f"💾 Memory: {args.memory_path}")
    print(f"🔍 Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    print()
    
    try:
        # Initialize components
        print("🔧 Initializing components...")
        memory = RAGMemory(db_path=args.memory_path)
        diagnostics = SelfDiagnostics()
        healing = SelfHealing(config_path=str(config_path), memory=memory, healing_enabled=not args.dry_run)
        print("✅ Components initialized")
        print()
        
        # Fetch current metrics
        print("📊 Fetching current metrics...")
        state = fetch_state()
        execution_stats = fetch_execution_stats()
        
        current_metrics = {
            "win_rate": state.get("win_rate", 0.0),
            "trades_today": state.get("trades_today", 0),
            "daily_pnl": state.get("daily_pnl", 0.0),
            "margin_utilization": state.get("margin_utilization", 0.0),
        }
        
        print(f"   Win Rate: {current_metrics['win_rate']:.1%}")
        print(f"   Trades Today: {current_metrics['trades_today']}")
        print(f"   Daily PnL: ₹{current_metrics['daily_pnl']:.2f}")
        print()
        
        # Run diagnostics
        print("🔍 Running diagnostics...")
        results = diagnostics.run_diagnostics(current_metrics)
        
        if not results:
            print("✅ No anomalies detected - system is healthy!")
            print()
        else:
            print(f"⚠️  Detected {len(results)} anomaly(ies):")
            print()
            
            for result in results:
                print(f"   [{result.severity}] {result.anomaly_type.value}")
                print(f"      {result.message}")
                print(f"      Score: {result.score:.2f}")
                print(f"      Recommended: {', '.join(result.recommended_actions[:2])}")
                print()
            
            # Apply healing
            if not args.dry_run:
                print("🔧 Applying healing actions...")
                healing_results = []
                
                for diagnostic in results:
                    if diagnostic.severity in ["HIGH", "CRITICAL"]:
                        healing_result = healing.apply_healing(diagnostic)
                        if healing_result:
                            healing_results.append(healing_result)
                            if healing_result.success:
                                print(f"   ✅ {healing_result.action.value}: {healing_result.message}")
                            else:
                                print(f"   ⚠️  {healing_result.action.value}: {healing_result.message}")
                
                if not healing_results:
                    print("   ℹ️  No healing actions applied (low severity or no action needed)")
                print()
            else:
                print("🔍 DRY RUN: Would apply healing actions:")
                for diagnostic in results:
                    if diagnostic.severity in ["HIGH", "CRITICAL"]:
                        print(f"   - {diagnostic.anomaly_type.value}: {', '.join(diagnostic.recommended_actions[:2])}")
                print()
        
        # Show healing history
        history = healing.get_healing_history(limit=5)
        if history:
            print("📚 Recent Healing History:")
            for h in history:
                status = "✅" if h.success else "❌"
                print(f"   {status} {h.action.value}: {h.message}")
                print(f"      Time: {h.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
            print()
        
        print("=" * 60)
        print("✅ Self-healing cycle complete!")
        print("=" * 60)
        
    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Self-healing failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()





