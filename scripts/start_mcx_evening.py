#!/usr/bin/env python3
"""
MCX Evening Session Trading
Start MCX commodities trading (5:00 PM - 11:30 PM)

Usage:
    python3 scripts/start_mcx_evening.py
"""
import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from kiteconnect import KiteConnect
from packages.core.config import load_config
from packages.core.instruments import InstrumentManager
from packages.core.orchestrator import Orchestrator
import structlog

logger = structlog.get_logger(__name__)


async def start_mcx_trading():
    """Start MCX evening session trading"""

    print("=" * 70)
    print("🌙 MCX EVENING SESSION TRADER")
    print("=" * 70)
    print(f"Current Time: {datetime.now().strftime('%H:%M:%S IST')}")
    print(f"Session: 5:00 PM - 11:30 PM")
    print()

    # Check environment variables
    kite_api_key = os.getenv("KITE_API_KEY")
    kite_access_token = os.getenv("KITE_ACCESS_TOKEN")

    if not kite_api_key or not kite_access_token:
        print("❌ Missing KITE_API_KEY or KITE_ACCESS_TOKEN")
        print("   Please set these environment variables first")
        return

    print("✅ Kite credentials found")

    # Initialize Kite client
    kite = KiteConnect(api_key=kite_api_key)
    kite.set_access_token(kite_access_token)

    print("✅ Kite client initialized")

    # Fetch MCX instruments
    print("\n📊 Fetching MCX instruments...")
    try:
        mcx_instruments = kite.instruments("MCX")
        print(f"✅ Fetched {len(mcx_instruments)} MCX instruments")

        # Filter for liquid commodities
        target_symbols = ["GOLDM", "GOLD", "SILVER", "CRUDEOIL", "NATURALGAS"]
        filtered = []

        print("\n🔍 Finding liquid commodities:")
        for symbol in target_symbols:
            # Find near-month futures
            matches = [
                inst for inst in mcx_instruments
                if inst['name'] == symbol and inst['instrument_type'] == 'FUT'
            ]

            # Sort by expiry (nearest first)
            if matches:
                matches.sort(key=lambda x: x.get('expiry', ''))
                nearest = matches[0]
                filtered.append(nearest)

                print(f"  ✓ {symbol:12s} -> {nearest['tradingsymbol']:25s} (Expiry: {nearest.get('expiry', 'N/A')})")

        if not filtered:
            print("❌ No MCX instruments found for trading")
            return

        print(f"\n✅ Selected {len(filtered)} MCX contracts for trading")

        # Extract tokens
        mcx_tokens = [inst['instrument_token'] for inst in filtered]
        print(f"   Tokens: {mcx_tokens}")

        # Load config
        print("\n⚙️  Loading MCX configuration...")
        config = load_config("configs/mcx_evening.yaml")
        print("✅ Configuration loaded")

        # Override universe with MCX tokens
        print(f"\n🌐 Setting up MCX trading universe ({len(mcx_tokens)} instruments)...")

        # Note: You would need to modify the orchestrator to accept
        # manual token list instead of building from config
        print("\n" + "=" * 70)
        print("⚠️  NEXT STEPS NEEDED:")
        print("=" * 70)
        print()
        print("The system needs a minor update to support manual MCX token lists.")
        print("Two options:")
        print()
        print("1. Quick Test (Manual)")
        print("   - Use Kite web/app to place MCX trades manually")
        print("   - Monitor with PremiumAdaptiveTrend signals")
        print("   - Good for testing MCX viability tonight")
        print()
        print("2. Full Integration (Requires code update)")
        print("   - Update instruments.py to handle MCX universe building")
        print("   - Add MCX-specific logic to orchestrator")
        print("   - Estimated: 30-45 minutes of development")
        print()
        print("=" * 70)
        print()
        print("📋 MCX INSTRUMENTS READY FOR MANUAL TRADING:")
        print()
        for inst in filtered:
            print(f"   {inst['tradingsymbol']:25s} | Token: {inst['instrument_token']:10d} | Lot: {inst.get('lot_size', 1):5d}")
        print()
        print("Current MCX Price Check:")
        print()

        # Fetch current quotes
        quote_keys = [f"MCX:{inst['tradingsymbol']}" for inst in filtered[:3]]
        try:
            quotes = kite.quote(quote_keys)
            for key, data in quotes.items():
                print(f"   {key:30s} | LTP: ₹{data.get('last_price', 0):10.2f} | Volume: {data.get('volume', 0):8d}")
        except Exception as e:
            print(f"   (Could not fetch quotes: {e})")

        print()
        print("=" * 70)

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(start_mcx_trading())
