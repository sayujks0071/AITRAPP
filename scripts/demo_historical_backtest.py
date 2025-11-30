#!/usr/bin/env python3
"""
Quick Demo: Historical Data Backtest
=====================================

Simplified demo using existing Kite integration (no MCP required for now).
Shows how to backtest with real historical data and tweak parameters via CLI.

Usage:
    python3 scripts/demo_historical_backtest.py
"""

import argparse
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Tuple

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from kiteconnect import KiteConnect
except ImportError:
    print("⚠️  KiteConnect not installed. Install with: pip install kiteconnect")
    sys.exit(1)


def demo_search_instruments():
    """Demo: Search for instruments"""
    print("\n" + "="*60)
    print("📊 DEMO 1: Search for NIFTY Instruments")
    print("="*60)

    api_key = os.getenv("KITE_API_KEY")
    access_token = os.getenv("KITE_ACCESS_TOKEN")

    if not api_key or not access_token:
        print("❌ Error: KITE_API_KEY and KITE_ACCESS_TOKEN must be set")
        print("\nSet them with:")
        print("  export KITE_API_KEY='your_key'")
        print("  export KITE_ACCESS_TOKEN='your_token'")
        return False

    try:
        kite = KiteConnect(api_key=api_key)
        kite.set_access_token(access_token)

        # Get instruments
        print("🔍 Fetching instruments from NSE...")
        instruments = kite.instruments("NSE")

        # Filter for NIFTY
        nifty_instruments = [i for i in instruments if "NIFTY" in i["tradingsymbol"]]

        print(f"✅ Found {len(nifty_instruments)} NIFTY-related instruments")
        print("\nSample instruments:")
        for inst in nifty_instruments[:5]:
            print(f"  - {inst['tradingsymbol']} (Token: {inst['instrument_token']})")

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def demo_fetch_historical_data(instrument_token: int, interval: str, days: int):
    """Demo: Fetch historical OHLC data"""
    print("\n" + "="*60)
    print("📈 DEMO 2: Fetch Historical Data for NIFTY 50")
    print("="*60)

    api_key = os.getenv("KITE_API_KEY")
    access_token = os.getenv("KITE_ACCESS_TOKEN")

    if not api_key or not access_token:
        print("❌ Error: Credentials not set")
        return False

    try:
        kite = KiteConnect(api_key=api_key)
        kite.set_access_token(access_token)

        to_date = datetime.now()
        from_date = to_date - timedelta(days=days)

        print(f"📅 Fetching data from {from_date.date()} to {to_date.date()}")
        print(f"🎯 Instrument Token: {instrument_token}")
        print(f"⏱️  Interval: {interval}")

        # Fetch historical data
        historical = kite.historical_data(
            instrument_token=instrument_token,
            from_date=from_date,
            to_date=to_date,
            interval=interval
        )

        print(f"✅ Fetched {len(historical)} candles")

        if historical:
            print("\n📊 Sample data (first 3 candles):")
            for i, candle in enumerate(historical[:3]):
                print(f"\n  Candle {i+1}:")
                print(f"    Time:  {candle['date']}")
                print(f"    Open:  {candle['open']}")
                print(f"    High:  {candle['high']}")
                print(f"    Low:   {candle['low']}")
                print(f"    Close: {candle['close']}")
                print(f"    Volume: {candle['volume']}")

            print(f"\n  ... and {len(historical) - 3} more candles")

            # Calculate some basic stats
            closes = [c['close'] for c in historical]
            avg_price = sum(closes) / len(closes)
            min_price = min(closes)
            max_price = max(closes)
            price_range = max_price - min_price

            print("\n📈 Summary Statistics:")
            print(f"  Average Close: ₹{avg_price:.2f}")
            print(f"  Min Price:     ₹{min_price:.2f}")
            print(f"  Max Price:     ₹{max_price:.2f}")
            print(f"  Range:         ₹{price_range:.2f} ({(price_range/avg_price*100):.2f}%)")

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def _calculate_rsi(closes: List[float], period: int = 14) -> Optional[float]:
    """Simple RSI calculation"""
    if len(closes) < period + 1:
        return None

    gains: List[float] = []
    losses: List[float] = []

    for i in range(1, len(closes)):
        change = closes[i] - closes[i - 1]
        if change > 0:
            gains.append(change)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(change))

    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def _calculate_macd(
    closes: List[float],
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> Tuple[Optional[float], Optional[float]]:
    """Lightweight MACD calculation (EMA-based)."""
    if len(closes) < slow + signal:
        return None, None

    def ema(values: List[float], period: int) -> float:
        k = 2 / (period + 1)
        ema_val = values[0]
        for v in values[1:]:
            ema_val = v * k + ema_val * (1 - k)
        return ema_val

    macd_line = ema(closes[-slow:], fast) - ema(closes[-slow:], slow)
    signal_line = ema([macd_line] * signal, signal)
    return macd_line, signal_line


def demo_simple_backtest(
    instrument_token: int,
    interval: str,
    days: int,
    rsi_buy: float,
    rsi_sell: float,
    use_macd: bool,
):
    """Demo: Simple RSI (optionally MACD-filtered) backtest"""
    print("\n" + "="*60)
    print("🎯 DEMO 3: Simple RSI Backtest")
    print("="*60)

    api_key = os.getenv("KITE_API_KEY")
    access_token = os.getenv("KITE_ACCESS_TOKEN")

    if not api_key or not access_token:
        print("❌ Error: Credentials not set")
        return False

    try:
        kite = KiteConnect(api_key=api_key)
        kite.set_access_token(access_token)

        to_date = datetime.now()
        from_date = to_date - timedelta(days=days)

        print(f"📅 Backtest period: {from_date.date()} to {to_date.date()}")
        print(f"📊 Strategy: RSI Mean Reversion (configurable)")
        print(f"   - Entry: RSI < {rsi_buy} (oversold)")
        print(f"   - Exit: RSI > {rsi_sell} (overbought)")
        if use_macd:
            print("   - MACD filter: require MACD > Signal for longs")

        # Fetch data
        historical = kite.historical_data(
            instrument_token=instrument_token,
            from_date=from_date,
            to_date=to_date,
            interval=interval
        )

        print(f"\n✅ Loaded {len(historical)} candles")

        # Backtest
        signals = []
        position = None
        entry_idx = None

        for i in range(14, len(historical)):  # Need 14 candles for RSI
            closes = [c['close'] for c in historical[:i+1]]
            rsi = _calculate_rsi(closes, period=14)
            macd_line, macd_signal = _calculate_macd(closes) if use_macd else (None, None)

            if rsi is None:
                continue

            candle = historical[i]

            # Entry signal
            macd_ok = True if not use_macd else (macd_line is not None and macd_signal is not None and macd_line > macd_signal)

            if position is None and rsi < rsi_buy and macd_ok:
                signals.append({
                    "type": "BUY",
                    "time": candle['date'],
                    "price": candle['close'],
                    "rsi": rsi,
                    "macd": macd_line,
                    "macd_signal": macd_signal,
                })
                position = candle['close']
                entry_idx = i

            # Exit signal
            elif position is not None and rsi > rsi_sell:
                entry_price = position
                exit_price = candle['close']
                pnl = exit_price - entry_price
                pnl_pct = (pnl / entry_price) * 100

                signals.append({
                    "type": "SELL",
                    "time": candle['date'],
                    "price": candle['close'],
                    "rsi": rsi,
                    "macd": macd_line,
                    "macd_signal": macd_signal,
                    "pnl": pnl,
                    "pnl_pct": pnl_pct
                })
                position = None
                entry_idx = None

        print(f"\n🎯 Backtest Results:")
        print(f"   Total Signals: {len(signals)}")

        buy_signals = [s for s in signals if s['type'] == 'BUY']
        sell_signals = [s for s in signals if s['type'] == 'SELL']

        print(f"   Buy Signals:   {len(buy_signals)}")
        print(f"   Sell Signals:  {len(sell_signals)}")

        if sell_signals:
            total_pnl = sum(s['pnl'] for s in sell_signals)
            avg_pnl_pct = sum(s['pnl_pct'] for s in sell_signals) / len(sell_signals)

            print(f"\n💰 P&L Analysis:")
            print(f"   Total P&L:     ₹{total_pnl:.2f}")
            print(f"   Avg P&L %:     {avg_pnl_pct:.2f}%")

            print(f"\n📋 Trades:")
            for i, sell in enumerate(sell_signals, 1):
                print(f"\n   Trade {i}:")
                print(f"     Exit Time:   {sell['time']}")
                print(f"     Exit Price:  ₹{sell['price']:.2f}")
                print(f"     Exit RSI:    {sell['rsi']:.1f}")
                if use_macd:
                    print(f"     Exit MACD:   {sell.get('macd'):.3f} vs Signal {sell.get('macd_signal'):.3f}")
                print(f"     P&L:         ₹{sell['pnl']:.2f} ({sell['pnl_pct']:.2f}%)")
        else:
            print("\n   No completed trades in this period")

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all demos"""
    parser = argparse.ArgumentParser(description="Historical data + quick RSI/MACD backtest.")
    parser.add_argument("--instrument-token", type=int, default=256265, help="Kite instrument token (default: NIFTY 50)")
    parser.add_argument("--interval", default="5minute", help="Kite interval (e.g., 1minute, 5minute, 15minute, day)")
    parser.add_argument("--fetch-days", type=int, default=7, help="Days to fetch for the historical data demo")
    parser.add_argument("--backtest-days", type=int, default=3, help="Days to backtest for the RSI demo")
    parser.add_argument("--rsi-buy", type=float, default=25.0, help="RSI buy threshold (oversold)")
    parser.add_argument("--rsi-sell", type=float, default=75.0, help="RSI sell threshold (overbought)")
    parser.add_argument("--macd-filter", action="store_true", help="Require MACD > Signal for long entries")
    args = parser.parse_args()

    print("\n" + "="*60)
    print("🚀 HISTORICAL DATA BACKTEST DEMO")
    print("="*60)
    print("\nThis demo shows how to:")
    print("  1. Search for instruments")
    print("  2. Fetch historical OHLC data from Kite")
    print("  3. Run a configurable RSI (+MACD) backtest")
    print("\n" + "="*60)

    # Check credentials
    if not os.getenv("KITE_API_KEY") or not os.getenv("KITE_ACCESS_TOKEN"):
        print("\n❌ ERROR: Kite credentials not set!")
        print("\nPlease set your Kite credentials:")
        print("  export KITE_API_KEY='your_api_key'")
        print("  export KITE_ACCESS_TOKEN='your_access_token'")
        print("\nGet your access token by running:")
        print("  python3 scripts/kite_express_login.py")
        return

    # Run demos
    success1 = demo_search_instruments()
    if success1:
        success2 = demo_fetch_historical_data(
            instrument_token=args.instrument_token,
            interval=args.interval,
            days=args.fetch_days,
        )
        if success2:
            demo_simple_backtest(
                instrument_token=args.instrument_token,
                interval=args.interval,
                days=args.backtest_days,
                rsi_buy=args.rsi_buy,
                rsi_sell=args.rsi_sell,
                use_macd=args.macd_filter,
            )

    print("\n" + "="*60)
    print("✅ DEMO COMPLETE")
    print("="*60)
    print("\n📚 Next Steps:")
    print("  1. Review the data fetched above")
    print("  2. Modify RSI/MACD thresholds (--rsi-buy/--rsi-sell/--macd-filter)")
    print("  3. Test on different timeframes (--interval 1minute|15minute|day)")
    print("  4. Swap instruments with --instrument-token (e.g., BANKNIFTY=260105)")
    print("  5. Integrate with full backtest engine or paper replay")
    print("\n💡 Full MCP integration coming soon!")
    print("   For now, use KiteConnect SDK directly as shown above.\n")


if __name__ == "__main__":
    main()
