#!/usr/bin/env python3
"""
Strategic Memory Engine (SME) Explorer - Level 8
===============================================

CLI tool to interrogate your bot's long-term institutional memory.

Usage:
    python3 scripts/run_sme_analysis.py --regime "HIGH_VOL"
    python3 scripts/run_sme_analysis.py --strategy "trend_credit_spread"
    python3 scripts/run_sme_analysis.py --day-of-week "FRIDAY"
    python3 scripts/run_sme_analysis.py --lineage
    python3 scripts/run_sme_analysis.py --abandoned
"""

import argparse
import json
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from packages.core.intelligence.sme import StrategicMemoryEngine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("sme_explorer")


def print_top_performers(sme: StrategicMemoryEngine, regime: str, limit: int = 5):
    """Print top performing strategies for a regime"""
    # Use the query_best_strategies method
    best_strategies = sme.query_best_strategies(regime)
    
    if not best_strategies:
        print(f"❌ No performance data found for regime: {regime}")
        print("   (Need at least 5 trades per strategy)")
        return
    
    print(f"\n🏆 Top Performers in {regime}:")
    print("=" * 60)
    
    # Get full performance matrix for additional details
    matrix = sme._load(sme.matrix_file)
    regime_data = matrix.get(regime, {})
    
    for i, (strategy_name, win_rate) in enumerate(best_strategies[:limit], 1):
        stats = regime_data.get(strategy_name, {})
        total_pnl = stats.get("pnl", 0.0)
        total_trades = stats.get("trades", 0)
        avg_pnl = total_pnl / total_trades if total_trades > 0 else 0.0
        
        print(f"\n{i}. {strategy_name}")
        print(f"   Win Rate: {win_rate*100:.1f}%")
        print(f"   Total PnL: ₹{total_pnl:,.2f}")
        print(f"   Avg PnL/Trade: ₹{avg_pnl:.2f}")
        print(f"   Total Trades: {total_trades}")


def print_seasonality(sme: StrategicMemoryEngine, strategy_name: str = None, pattern_type: str = None):
    """Print seasonality patterns"""
    patterns = sme.get_seasonality_patterns(
        strategy_name=strategy_name,
        pattern_type=pattern_type
    )
    
    if not patterns:
        print("❌ No seasonality patterns found")
        return
    
    print(f"\n📅 Seasonality Patterns:")
    if strategy_name:
        print(f"   Strategy: {strategy_name}")
    if pattern_type:
        print(f"   Type: {pattern_type}")
    print("=" * 60)
    
    # Group by pattern type
    by_type = {}
    for pattern in patterns:
        ptype = pattern.get("pattern_type", "UNKNOWN")
        if ptype not in by_type:
            by_type[ptype] = []
        by_type[ptype].append(pattern)
    
    for ptype, pats in by_type.items():
        print(f"\n{ptype}:")
        for pat in sorted(pats, key=lambda x: x.get("win_rate", 0), reverse=True):
            value = pat.get("pattern_value", "N/A")
            win_rate = pat.get("win_rate", 0.0)
            avg_pnl = pat.get("avg_pnl", 0.0)
            trades = pat.get("total_trades", 0)
            print(f"   {value}: Win Rate {win_rate:.1f}%, Avg PnL ₹{avg_pnl:.2f}, Trades: {trades}")


def print_lineage(sme: StrategicMemoryEngine):
    """Print strategy lineage tree"""
    tree = sme._load(sme.lineage_file)
    
    if not tree:
        print("❌ No strategy lineage data found")
        return
    
    print("\n🌳 Strategy Lineage Tree:")
    print("=" * 60)
    
    # Find root strategies (no parent)
    roots = [name for name, info in tree.items() if not info.get("parent")]
    children = {name: [] for name in tree.keys()}
    
    for name, info in tree.items():
        parent = info.get("parent")
        if parent:
            if parent not in children:
                children[parent] = []
            children[parent].append(name)
        # Also check children list in the entry itself
        if "children" in info:
            for child in info.get("children", []):
                if child not in children.get(name, []):
                    if name not in children:
                        children[name] = []
                    children[name].append(child)
    
    def print_node(name: str, indent: int = 0):
        if name not in tree:
            return
        info = tree[name]
        
        print("  " * indent + f"📦 {name}")
        
        if info.get("reason"):
            print("  " * (indent + 1) + f"   Reason: {info.get('reason')}")
        
        if info.get("parent"):
            print("  " * (indent + 1) + f"   Parent: {info.get('parent')}")
        
        if info.get("diff"):
            print("  " * (indent + 1) + f"   Config Diff: {json.dumps(info.get('diff'), indent=2)}")
        
        for child in children.get(name, []):
            print_node(child, indent + 1)
    
    for root in roots:
        print_node(root)


def print_abandoned(sme: StrategicMemoryEngine):
    """Print abandoned strategies"""
    tree = sme._load(sme.lineage_file)
    abandoned = [
        (name, info) for name, info in tree.items()
        if info.get("status") == "ABANDONED"
    ]
    
    if not abandoned:
        print("✅ No abandoned strategies found")
        return
    
    print("\n🗑️  Abandoned Strategies:")
    print("=" * 60)
    
    for name, info in abandoned:
        reason = info.get("abandoned_reason", "No reason provided")
        timestamp = info.get("timestamp", "N/A")
        
        print(f"\n❌ {name}")
        print(f"   Timestamp: {timestamp}")
        print(f"   Reason: {reason}")


def print_regime_matrix(sme: StrategicMemoryEngine):
    """Print regime fit matrix"""
    matrix = sme._load(sme.matrix_file)
    
    if not matrix:
        print("❌ No regime performance data found")
        return
    
    print("\n📊 Regime Fit Matrix (Win Rate %):")
    print("=" * 60)
    
    # Get all unique regimes and strategies
    all_regimes = sorted(matrix.keys())
    all_strategies = set()
    for regime_data in matrix.values():
        all_strategies.update(regime_data.keys())
    all_strategies = sorted(all_strategies)
    
    if not all_regimes or not all_strategies:
        print("   No regime data available")
        return
    
    # Print header
    header = f"{'Strategy':<30}"
    for regime in all_regimes:
        header += f" {regime[:15]:>15}"
    print(header)
    print("-" * len(header))
    
    # Print each strategy
    for strategy_name in all_strategies:
        row = f"{strategy_name[:30]:<30}"
        for regime in all_regimes:
            stats = matrix[regime].get(strategy_name, {})
            if stats.get("trades", 0) >= 5:
                win_rate = (stats["wins"] / stats["trades"] * 100) if stats["trades"] > 0 else 0.0
                row += f" {win_rate:>14.1f}%"
            else:
                row += f" {'N/A':>15}"
        print(row)


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Strategic Memory Engine (SME) Explorer - Level 8"
    )
    parser.add_argument(
        "--regime",
        type=str,
        help="Query top performers for a specific regime (e.g., HIGH_VOL, LOW_MEAN_REVERT)"
    )
    parser.add_argument(
        "--strategy",
        type=str,
        help="Query seasonality patterns for a specific strategy"
    )
    parser.add_argument(
        "--day-of-week",
        type=str,
        help="Query day of week patterns (e.g., FRIDAY, MONDAY)"
    )
    parser.add_argument(
        "--lineage",
        action="store_true",
        help="Show strategy lineage tree"
    )
    parser.add_argument(
        "--abandoned",
        action="store_true",
        help="Show abandoned strategies"
    )
    parser.add_argument(
        "--matrix",
        action="store_true",
        help="Show regime fit matrix"
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default="data/sme",
        help="Directory containing SME data files"
    )
    
    args = parser.parse_args()
    
    # Initialize SME
    sme = StrategicMemoryEngine(data_dir=args.data_dir)
    
    print("=" * 60)
    print("🧠 STRATEGIC MEMORY ENGINE (SME) - LEVEL 8")
    print("=" * 60)
    print(f"📁 Data Directory: {args.data_dir}")
    print("")
    
    # Execute queries
    if args.regime:
        print_top_performers(sme, args.regime.upper())
    
    if args.strategy or args.day_of_week:
        pattern_type = "DAY_OF_WEEK" if args.day_of_week else None
        print_seasonality(sme, strategy_name=args.strategy, pattern_type=pattern_type)
    
    if args.lineage:
        print_lineage(sme)
    
    if args.abandoned:
        print_abandoned(sme)
    
    if args.matrix:
        print_regime_matrix(sme)
    
    # If no specific query, show summary
    if not any([args.regime, args.strategy, args.day_of_week, args.lineage, args.abandoned, args.matrix]):
        print("ℹ️  No query specified. Use --help to see available options.")
        print("\nExample queries:")
        print("  python3 scripts/run_sme_analysis.py --regime HIGH_VOL")
        print("  python3 scripts/run_sme_analysis.py --strategy trend_credit_spread")
        print("  python3 scripts/run_sme_analysis.py --lineage")
        print("  python3 scripts/run_sme_analysis.py --matrix")
    
    print("\n" + "=" * 60)
    print("✅ SME Analysis Complete")
    print("=" * 60)


if __name__ == "__main__":
    main()

