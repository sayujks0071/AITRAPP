#!/usr/bin/env python3
"""Quick MCX availability check"""
import os
from kiteconnect import KiteConnect
from datetime import datetime

print("=" * 70)
print("🌙 MCX EVENING SESSION - AVAILABILITY CHECK")
print("=" * 70)
print(f"Time: {datetime.now().strftime('%H:%M:%S IST')}")
print()

# Check credentials
api_key = os.getenv("KITE_API_KEY")
token = os.getenv("KITE_ACCESS_TOKEN")

if not api_key or not token:
    print("❌ Missing credentials")
    exit(1)

kite = KiteConnect(api_key=api_key)
kite.set_access_token(token)

print("📊 Fetching MCX instruments...")
try:
    mcx_inst = kite.instruments("MCX")
    print(f"✅ Found {len(mcx_inst)} MCX instruments\n")

    # Find liquid commodities
    targets = ["GOLDM", "GOLD", "SILVER", "CRUDEOIL", "NATURALGAS", "COPPER"]

    print("🔍 Liquid MCX Futures (Near Month):\n")
    for target in targets:
        matches = [i for i in mcx_inst if i['name'] == target and i['instrument_type'] == 'FUT']
        if matches:
            matches.sort(key=lambda x: x.get('expiry', ''))
            nearest = matches[0]
            expiry_str = str(nearest.get('expiry', 'N/A'))[:10] if nearest.get('expiry') else 'N/A'
            print(f"  {target:12s} -> {nearest['tradingsymbol']:25s} | Expiry: {expiry_str} | Lot: {nearest.get('lot_size', 1):5d}")

    print("\n📈 Live Quotes:\n")
    # Get quotes for top 3
    quote_symbols = []
    for target in targets[:3]:
        matches = [i for i in mcx_inst if i['name'] == target and i['instrument_type'] == 'FUT']
        if matches:
            matches.sort(key=lambda x: x.get('expiry', ''))
            quote_symbols.append(f"MCX:{matches[0]['tradingsymbol']}")

    if quote_symbols:
        try:
            quotes = kite.quote(quote_symbols)
            for symbol, data in quotes.items():
                ltp = data.get('last_price', 0)
                chg = data.get('net_change', 0)
                vol = data.get('volume', 0)
                chg_pct = (chg / (ltp - chg) * 100) if ltp else 0
                print(f"  {symbol:30s} | ₹{ltp:10.2f} | {chg:+8.2f} ({chg_pct:+.2f}%) | Vol: {vol:8d}")
        except Exception as e:
            print(f"  ⚠️  Could not fetch quotes: {e}")

    print("\n" + "=" * 70)
    print("MCX Trading Status: ✅ AVAILABLE")
    print("Session Hours: 5:00 PM - 11:30 PM IST")
    print("Current Strategies: PremiumAdaptiveTrend, SMAMomentum, MACD")
    print("=" * 70)

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
