#!/usr/bin/env python3
"""
Position Reconciliation Script

Reconciles positions between system database and Kite API.
Identifies discrepancies and optionally auto-syncs them.

Usage:
    python3 scripts/reconcile_positions.py                # View only
    python3 scripts/reconcile_positions.py --auto-sync    # Auto-sync discrepancies
"""
import asyncio
import argparse
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from kiteconnect import KiteConnect
from packages.core.position_reconciliation import PositionReconciler
from packages.storage.database import Database
from packages.core.config import load_config
import structlog

logger = structlog.get_logger(__name__)


async def main():
    parser = argparse.ArgumentParser(description="Reconcile positions with Kite API")
    parser.add_argument(
        "--auto-sync",
        action="store_true",
        help="Automatically sync discrepancies"
    )
    parser.add_argument(
        "--config",
        default="configs/app.yaml",
        help="Path to config file"
    )
    args = parser.parse_args()

    # Load config
    config = load_config(args.config)

    # Initialize Kite client
    kite_api_key = os.getenv("KITE_API_KEY")
    kite_access_token = os.getenv("KITE_ACCESS_TOKEN")

    if not kite_api_key or not kite_access_token:
        print("❌ Missing KITE_API_KEY or KITE_ACCESS_TOKEN environment variables")
        sys.exit(1)

    kite = KiteConnect(api_key=kite_api_key)
    kite.set_access_token(kite_access_token)

    # Initialize database
    db = Database(config.database if hasattr(config, "database") else {})
    await db.initialize()

    # Create reconciler
    reconciler = PositionReconciler(kite, db)

    # Run reconciliation
    print("\n" + "=" * 70)
    print("POSITION RECONCILIATION")
    print("=" * 70)

    if args.auto_sync:
        print("\n🔄 Running reconciliation with auto-sync enabled...\n")
        result = await reconciler.reconcile_and_sync(auto_sync=True)
    else:
        print("\n🔍 Running reconciliation (view only)...\n")
        result = await reconciler.reconcile()

    # Print summary
    print(result.summary())

    # Print detailed discrepancies
    if not result.is_clean():
        print("\n" + "=" * 70)
        print("DETAILED DISCREPANCIES")
        print("=" * 70)

        if result.missing_in_system:
            print("\n📥 Positions in Kite but NOT in system:")
            for pos in result.missing_in_system:
                print(f"  - {pos['symbol']}: Qty {pos['kite_qty']} @ ₹{pos['kite_avg_price']:.2f}")

        if result.missing_in_kite:
            print("\n📤 Positions in system but NOT in Kite:")
            for pos in result.missing_in_kite:
                print(f"  - {pos['symbol']}: Qty {pos['system_qty']} @ ₹{pos['system_entry_price']:.2f}")

        if result.quantity_mismatches:
            print("\n⚠️  Quantity mismatches:")
            for pos in result.quantity_mismatches:
                print(f"  - {pos['symbol']}: Kite={pos['kite_qty']} vs System={pos['system_qty']} (diff: {pos['difference']})")

        if result.price_mismatches:
            print("\n⚠️  Price mismatches:")
            for pos in result.price_mismatches:
                print(f"  - {pos['symbol']}: Kite=₹{pos['kite_price']:.2f} vs System=₹{pos['system_price']:.2f} (diff: ₹{pos['difference']:.2f})")

    print("\n" + "=" * 70)

    if not args.auto_sync and not result.is_clean():
        print("\n💡 Tip: Run with --auto-sync to automatically fix discrepancies")

    await db.close()


if __name__ == "__main__":
    asyncio.run(main())
