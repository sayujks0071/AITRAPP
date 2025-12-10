#!/usr/bin/env python3
"""
Live Paper Trade Monitor using Kite
====================================

Monitors your running paper trading session in real-time.
Shows positions, orders, P&L, and metrics.

Usage:
    # Continuous monitoring (updates every 30s)
    python3 scripts/monitor_paper_trade.py

    # Single snapshot
    python3 scripts/monitor_paper_trade.py --once

    # Custom refresh interval
    python3 scripts/monitor_paper_trade.py --interval 10

    # Watch specific metrics
    python3 scripts/monitor_paper_trade.py --watch pnl

    # Export to JSON
    python3 scripts/monitor_paper_trade.py --once --export snapshot.json
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from kiteconnect import KiteConnect
except ImportError:
    print("⚠️  KiteConnect not installed. Install with: pip install --break-system-packages kiteconnect")
    sys.exit(1)


class PaperTradeMonitor:
    """Monitor paper trading via Kite API"""

    def __init__(self):
        self.api_key = os.getenv("KITE_API_KEY")
        self.access_token = os.getenv("KITE_ACCESS_TOKEN")

        if not self.api_key or not self.access_token:
            print("❌ Error: KITE_API_KEY and KITE_ACCESS_TOKEN must be set")
            print("\nSet them with:")
            print("  export KITE_API_KEY='your_key'")
            print("  export KITE_ACCESS_TOKEN='your_token'")
            sys.exit(1)

        self.kite = KiteConnect(api_key=self.api_key)
        self.kite.set_access_token(self.access_token)

    def get_positions(self) -> Dict[str, Any]:
        """Fetch current positions"""
        try:
            positions = self.kite.positions()
            return positions
        except Exception as e:
            return {"error": str(e), "net": [], "day": []}

    def get_orders(self) -> List[Dict]:
        """Fetch today's orders"""
        try:
            orders = self.kite.orders()
            return orders
        except Exception as e:
            return []

    def get_holdings(self) -> List[Dict]:
        """Fetch holdings"""
        try:
            holdings = self.kite.holdings()
            return holdings
        except Exception as e:
            return []

    def get_margins(self) -> Dict[str, Any]:
        """Fetch account margins"""
        try:
            margins = self.kite.margins()
            return margins
        except Exception as e:
            return {}

    def get_profile(self) -> Dict[str, Any]:
        """Fetch user profile"""
        try:
            profile = self.kite.profile()
            return profile
        except Exception as e:
            return {}

    def calculate_pnl_summary(self, positions: Dict) -> Dict[str, float]:
        """Calculate P&L summary from positions"""
        net_positions = positions.get("net", [])

        total_pnl = 0.0
        realized_pnl = 0.0
        unrealized_pnl = 0.0

        for pos in net_positions:
            pnl = pos.get("pnl", 0) or 0
            total_pnl += pnl

            if pos.get("quantity", 0) == 0:
                realized_pnl += pnl
            else:
                unrealized_pnl += pnl

        return {
            "total": total_pnl,
            "realized": realized_pnl,
            "unrealized": unrealized_pnl
        }

    def format_snapshot(self) -> Dict[str, Any]:
        """Get complete trading snapshot"""
        print("📊 Fetching trading data...", end="", flush=True)

        positions = self.get_positions()
        orders = self.get_orders()
        margins = self.get_margins()
        profile = self.get_profile()
        pnl = self.calculate_pnl_summary(positions)

        print(" ✅")

        # Count active positions
        net_positions = positions.get("net", [])
        active_positions = [p for p in net_positions if p.get("quantity", 0) != 0]

        # Count orders by status
        order_stats = {}
        for order in orders:
            status = order.get("status", "UNKNOWN")
            order_stats[status] = order_stats.get(status, 0) + 1

        # Margin info
        equity_margin = margins.get("equity", {})
        available = equity_margin.get("available", {}).get("live_balance", 0)
        used = equity_margin.get("utilised", {}).get("debits", 0)

        return {
            "timestamp": datetime.now().isoformat(),
            "profile": {
                "user_id": profile.get("user_id", "N/A"),
                "user_name": profile.get("user_name", "N/A"),
                "email": profile.get("email", "N/A")
            },
            "pnl": pnl,
            "positions": {
                "total": len(net_positions),
                "active": len(active_positions),
                "closed": len(net_positions) - len(active_positions),
                "details": active_positions
            },
            "orders": {
                "total": len(orders),
                "by_status": order_stats,
                "recent": orders[-5:] if orders else []
            },
            "margin": {
                "available": available,
                "used": used,
                "total": available + used
            }
        }

    def display_snapshot(self, snapshot: Dict[str, Any], clear_screen: bool = True):
        """Display formatted snapshot"""
        if clear_screen:
            os.system('clear' if os.name != 'nt' else 'cls')

        print("\n" + "="*70)
        print("📊 LIVE PAPER TRADE MONITOR")
        print("="*70)

        # Timestamp
        timestamp = datetime.fromisoformat(snapshot["timestamp"])
        print(f"\n⏰ Time: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")

        # Profile
        profile = snapshot["profile"]
        print(f"👤 User: {profile['user_name']} ({profile['user_id']})")

        # P&L Section
        print("\n" + "-"*70)
        print("💰 P&L SUMMARY")
        print("-"*70)
        pnl = snapshot["pnl"]
        total_pnl = pnl["total"]
        realized = pnl["realized"]
        unrealized = pnl["unrealized"]

        # Color code P&L
        total_symbol = "🟢" if total_pnl >= 0 else "🔴"
        realized_symbol = "🟢" if realized >= 0 else "🔴"
        unrealized_symbol = "🟢" if unrealized >= 0 else "🔴"

        print(f"  {total_symbol} Total P&L:      ₹{total_pnl:,.2f}")
        print(f"  {realized_symbol} Realized:       ₹{realized:,.2f}")
        print(f"  {unrealized_symbol} Unrealized:     ₹{unrealized:,.2f}")

        # Positions Section
        print("\n" + "-"*70)
        print("📈 POSITIONS")
        print("-"*70)
        pos_info = snapshot["positions"]
        print(f"  Total Positions:  {pos_info['total']}")
        print(f"  Active:           {pos_info['active']}")
        print(f"  Closed:           {pos_info['closed']}")

        if pos_info["active"] > 0:
            print("\n  Active Positions:")
            for i, pos in enumerate(pos_info["details"][:10], 1):  # Show max 10
                symbol = pos.get("tradingsymbol", "UNKNOWN")
                qty = pos.get("quantity", 0)
                avg_price = pos.get("average_price", 0)
                ltp = pos.get("last_price", 0)
                pos_pnl = pos.get("pnl", 0)
                pos_symbol = "🟢" if pos_pnl >= 0 else "🔴"

                print(f"\n  {i}. {symbol}")
                print(f"     Qty: {qty:+,} | Avg: ₹{avg_price:.2f} | LTP: ₹{ltp:.2f}")
                print(f"     {pos_symbol} P&L: ₹{pos_pnl:,.2f}")

        # Orders Section
        print("\n" + "-"*70)
        print("📋 ORDERS (TODAY)")
        print("-"*70)
        order_info = snapshot["orders"]
        print(f"  Total Orders:     {order_info['total']}")

        if order_info["by_status"]:
            print("\n  By Status:")
            for status, count in order_info["by_status"].items():
                status_symbol = {
                    "COMPLETE": "✅",
                    "OPEN": "⏳",
                    "REJECTED": "❌",
                    "CANCELLED": "🚫"
                }.get(status, "❓")
                print(f"    {status_symbol} {status}: {count}")

        if order_info["recent"]:
            print("\n  Recent Orders (Last 5):")
            for i, order in enumerate(order_info["recent"], 1):
                symbol = order.get("tradingsymbol", "UNKNOWN")
                side = order.get("transaction_type", "?")
                qty = order.get("quantity", 0)
                status = order.get("status", "?")
                order_time = order.get("order_timestamp", "")

                side_symbol = "🟢" if side == "BUY" else "🔴"
                print(f"\n  {i}. {side_symbol} {side} {symbol} x{qty}")
                print(f"     Status: {status} | Time: {order_time}")

        # Margin Section
        print("\n" + "-"*70)
        print("💳 MARGIN")
        print("-"*70)
        margin = snapshot["margin"]
        utilization = (margin["used"] / margin["total"] * 100) if margin["total"] > 0 else 0

        print(f"  Available:        ₹{margin['available']:,.2f}")
        print(f"  Used:             ₹{margin['used']:,.2f}")
        print(f"  Total:            ₹{margin['total']:,.2f}")
        print(f"  Utilization:      {utilization:.1f}%")

        # Progress bar for margin
        bar_width = 40
        used_bars = int(bar_width * utilization / 100)
        bar = "█" * used_bars + "░" * (bar_width - used_bars)
        print(f"  [{bar}]")

        print("\n" + "="*70)
        print(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")
        print("="*70 + "\n")

    def monitor_loop(self, interval: int = 30, watch_metric: str = None):
        """Continuous monitoring loop"""
        print(f"🔄 Starting monitor (refresh every {interval}s)...")
        print("Press Ctrl+C to stop\n")

        try:
            while True:
                snapshot = self.format_snapshot()
                self.display_snapshot(snapshot, clear_screen=True)

                # Optional: Alert on specific metrics
                if watch_metric == "pnl":
                    pnl = snapshot["pnl"]["total"]
                    if pnl < -1000:
                        print("🚨 WARNING: P&L below -₹1000!")

                time.sleep(interval)

        except KeyboardInterrupt:
            print("\n\n✋ Monitoring stopped by user")
        except Exception as e:
            print(f"\n❌ Error in monitor loop: {e}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Live paper trade monitor")

    parser.add_argument(
        "--once",
        action="store_true",
        help="Show single snapshot and exit (no continuous monitoring)"
    )

    parser.add_argument(
        "--interval",
        type=int,
        default=30,
        help="Refresh interval in seconds (default: 30)"
    )

    parser.add_argument(
        "--watch",
        choices=["pnl", "positions", "orders"],
        help="Watch specific metric for alerts"
    )

    parser.add_argument(
        "--export",
        type=str,
        help="Export snapshot to JSON file"
    )

    parser.add_argument(
        "--raw",
        action="store_true",
        help="Output raw JSON instead of formatted display"
    )

    args = parser.parse_args()

    # Initialize monitor
    monitor = PaperTradeMonitor()

    # Get snapshot
    snapshot = monitor.format_snapshot()

    # Handle different modes
    if args.raw:
        # Raw JSON output
        print(json.dumps(snapshot, indent=2, default=str))

    elif args.export:
        # Export to file
        output_path = Path(args.export)
        output_path.write_text(json.dumps(snapshot, indent=2, default=str))
        print(f"✅ Snapshot exported to {output_path}")

    elif args.once:
        # Single snapshot
        monitor.display_snapshot(snapshot, clear_screen=False)

    else:
        # Continuous monitoring
        monitor.display_snapshot(snapshot, clear_screen=True)
        time.sleep(args.interval)
        monitor.monitor_loop(interval=args.interval, watch_metric=args.watch)


if __name__ == "__main__":
    main()
