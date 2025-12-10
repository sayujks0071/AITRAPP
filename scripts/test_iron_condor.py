#!/usr/bin/env python3
"""Test NIFTY Iron Condor Deployment - Simplified for quick testing"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from kiteconnect import KiteConnect
import os
from dotenv import load_dotenv

load_dotenv()

def main():
    print("=" * 60)
    print("  NIFTY IRON CONDOR TEST")
    print("=" * 60)
    print()

    # Initialize Kite
    api_key = os.getenv("KITE_API_KEY")
    access_token = os.getenv("KITE_ACCESS_TOKEN")

    if not api_key or not access_token:
        print("❌ Missing KITE_API_KEY or KITE_ACCESS_TOKEN in .env")
        return

    kite = KiteConnect(api_key=api_key)
    kite.set_access_token(access_token)

    try:
        # Get NIFTY spot
        print("📊 Fetching NIFTY spot price...")
        quote = kite.ltp(["NSE:NIFTY 50"])
        spot = quote["NSE:NIFTY 50"]["last_price"]
        print(f"   NIFTY Spot: ₹{spot:,.2f}")
        print()

        # Calculate ATM and iron condor strikes
        atm = round(spot / 50) * 50
        width = 100

        strikes = {
            "buy_put": atm - 200,
            "sell_put": atm - 100,
            "sell_call": atm + 100,
            "buy_call": atm + 200
        }

        print("🎯 Iron Condor Structure:")
        print(f"   ATM Strike: {atm}")
        print(f"   Buy Put:  {strikes['buy_put']} PE (far OTM)")
        print(f"   Sell Put: {strikes['sell_put']} PE (near OTM)")
        print(f"   Sell Call: {strikes['sell_call']} CE (near OTM)")
        print(f"   Buy Call: {strikes['buy_call']} CE (far OTM)")
        print()

        print("📅 To deploy this iron condor:")
        print(f"   1. Get option chain for NIFTY (current expiry)")
        print(f"   2. Find tradingsymbols for strikes: {list(strikes.values())}")
        print(f"   3. Place 4 orders (2 buys, 2 sells)")
        print()

        # Get next expiry options (example)
        print("🔍 Fetching available option contracts...")
        instruments = kite.instruments("NFO")
        nifty_options = [i for i in instruments if i["name"] == "NIFTY" and i["instrument_type"] in ["CE", "PE"]]

        # Get unique expiries
        expiries = sorted(set(i["expiry"] for i in nifty_options))[:3]
        print(f"   Next 3 expiries: {[str(e) for e in expiries]}")
        print()

        print("⚠️  This is a TEST script.")
        print("   To place actual orders, uncomment the order placement code below.")
        print()

        # Example order placement (COMMENTED OUT FOR SAFETY)
        print("# Example order code (DISABLED):")
        print(f"# kite.place_order(")
        print(f"#     variety=kite.VARIETY_REGULAR,")
        print(f"#     exchange=kite.EXCHANGE_NFO,")
        print(f"#     tradingsymbol='NIFTY24JANFUT',  # Replace with actual option symbol")
        print(f"#     transaction_type=kite.TRANSACTION_TYPE_BUY,")
        print(f"#     quantity=25,")
        print(f"#     product=kite.PRODUCT_NRML,")
        print(f"#     order_type=kite.ORDER_TYPE_MARKET")
        print(f"# )")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return

    print()
    print("✅ Test completed successfully")
    print("   System can connect to Kite and fetch data")

if __name__ == "__main__":
    main()
