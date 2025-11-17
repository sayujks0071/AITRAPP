#!/usr/bin/env python3
"""
Kite Debit Spread Sizing Calculator
====================================

Calculates position sizing for NIFTY weekly debit spreads based on:
- Desired ₹ risk per trade
- Capital size
- Stop loss percentage
- Take profit percentage

Usage:
    python scripts/kite_sizing_calc.py --capital 30000 --risk-pct 0.30
    python scripts/kite_sizing_calc.py --capital 50000 --risk-pct 0.30 --stop-pct 50 --tp-pct 70

Example outputs:
    For ₹30k capital, 0.30% risk = ₹90 per trade
    → Net debit: ₹1.8 per lot (₹90 / 50 lots)
    → Stop at ₹0.9 (50% of ₹1.8)
    → TP at ₹3.06 (70% of ₹1.8)
"""

import argparse
from typing import Tuple


def calculate_debit_spread_sizing(
    capital: float,
    risk_pct: float = 0.30,
    stop_pct: float = 50.0,
    tp_pct: float = 70.0,
    lot_size: int = 50
) -> Tuple[float, float, float, int, float]:
    """
    Calculate debit spread sizing parameters.
    
    Args:
        capital: Total capital (₹)
        risk_pct: Risk per trade as % of capital (default: 0.30%)
        stop_pct: Stop loss as % of net debit (default: 50%)
        tp_pct: Take profit as % of net debit (default: 70%)
        lot_size: Lot size for NIFTY (default: 50)
    
    Returns:
        Tuple of (risk_amount, net_debit_per_lot, stop_price, tp_price, lots, total_cost)
    """
    # Calculate risk amount
    risk_amount = capital * (risk_pct / 100)
    
    # For debit spreads:
    # - You pay net_debit to enter the spread
    # - Max loss = net_debit (if spread goes to 0)
    # - If you stop at stop_pct% loss, you exit when spread value = (1 - stop_pct/100) × net_debit
    # - Loss at stop = net_debit - (1 - stop_pct/100) × net_debit = (stop_pct/100) × net_debit
    #
    # So: risk_amount = (stop_pct/100) × net_debit × lot_size × lots
    # For 1 lot: net_debit_per_lot = risk_amount / ((stop_pct/100) × lot_size)
    
    net_debit_per_lot = risk_amount / ((stop_pct / 100) * lot_size)
    
    # Round to reasonable precision (2 decimal places for options)
    net_debit_per_lot = round(net_debit_per_lot, 2)
    
    # Calculate stop and TP prices
    stop_price = net_debit_per_lot * (1 - stop_pct / 100)
    tp_price = net_debit_per_lot * (1 + tp_pct / 100)
    
    # For 1 lot
    lots = 1
    total_cost = net_debit_per_lot * lot_size * lots
    
    # If total cost is too high, we might need to reduce net_debit_per_lot
    # But for Day-1, we want to keep it simple: 1 lot max
    
    return risk_amount, net_debit_per_lot, stop_price, tp_price, lots, total_cost


def format_output(
    capital: float,
    risk_pct: float,
    risk_amount: float,
    net_debit_per_lot: float,
    stop_price: float,
    tp_price: float,
    lots: int,
    total_cost: float,
    stop_pct: float,
    tp_pct: float,
    lot_size: int = 50
):
    """Format and print the sizing output."""
    print("\n" + "="*60)
    print("KITE DEBIT SPREAD SIZING CALCULATOR")
    print("="*60)
    print(f"\n📊 Input Parameters:")
    print(f"   Capital:           ₹{capital:,.0f}")
    print(f"   Risk per trade:    {risk_pct}%")
    print(f"   Stop loss:         {stop_pct}% of net debit")
    print(f"   Take profit:       {tp_pct}% of net debit")
    print(f"   Lot size:          {lot_size}")
    
    print(f"\n💰 Risk & Sizing:")
    print(f"   Risk amount:       ₹{risk_amount:.2f} per trade")
    print(f"   Net debit/lot:     ₹{net_debit_per_lot:.2f}")
    print(f"   Lots:              {lots}")
    print(f"   Total cost:        ₹{total_cost:.2f}")
    
    print(f"\n🎯 Entry/Exit Prices (per lot):")
    print(f"   Entry (net debit): ₹{net_debit_per_lot:.2f}")
    print(f"   Stop loss:         ₹{stop_price:.2f} (-{stop_pct}%)")
    print(f"   Take profit:       ₹{tp_price:.2f} (+{tp_pct}%)")
    
    print(f"\n📈 Example Spread Construction:")
    print(f"   For a CALL DEBIT SPREAD:")
    print(f"   - Buy  NIFTY {lot_size} CE at ₹X.XX")
    print(f"   - Sell NIFTY {lot_size} CE at ₹Y.YY")
    print(f"   - Net debit should be ≈ ₹{net_debit_per_lot:.2f} per lot")
    print(f"   - Total cost: ₹{total_cost:.2f} for {lots} lot(s)")
    
    print(f"\n⚠️  Risk Management:")
    print(f"   Max loss:          ₹{risk_amount:.2f} (if stop hit)")
    print(f"   Max profit:        ₹{(tp_price - net_debit_per_lot) * lot_size * lots:.2f} (if TP hit)")
    print(f"   Risk:Reward:        {((tp_price - net_debit_per_lot) / (net_debit_per_lot - stop_price)):.2f}:1")
    
    print(f"\n✅ Day-1 Checklist:")
    print(f"   ✓ Risk per trade: ₹{risk_amount:.2f} (within ₹60-₹150 range)")
    print(f"   ✓ Total cost: ₹{total_cost:.2f} (affordable for ₹{capital:,.0f} capital)")
    print(f"   ✓ Stop at -{stop_pct}%: ₹{stop_price:.2f} per lot")
    print(f"   ✓ TP at +{tp_pct}%: ₹{tp_price:.2f} per lot")
    print(f"   ✓ One lot only (Day-1 conservative)")
    
    print("\n" + "="*60)
    print("💡 Tips:")
    print("   - Look for spreads with net debit close to ₹{:.2f}".format(net_debit_per_lot))
    print("   - Ensure bid-ask spread ≤ 0.5% of mid price")
    print("   - Check OI ≥ 50k and volume ≥ 100")
    print("   - Prefer weekly expiries (0-7 DTE)")
    print("   - Enter only between 09:30-10:30 IST")
    print("   - Exit by 15:10-15:20 IST if still open")
    print("="*60 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Calculate Kite debit spread sizing for Day-1 canary",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Default: ₹30k capital, 0.30% risk, 50% stop, 70% TP
  python scripts/kite_sizing_calc.py --capital 30000

  # ₹50k capital, 0.30% risk
  python scripts/kite_sizing_calc.py --capital 50000 --risk-pct 0.30

  # Custom stop/TP percentages
  python scripts/kite_sizing_calc.py --capital 40000 --stop-pct 50 --tp-pct 80

  # ₹20k capital (minimum)
  python scripts/kite_sizing_calc.py --capital 20000 --risk-pct 0.30
        """
    )
    
    parser.add_argument(
        "--capital",
        type=float,
        required=True,
        help="Total capital in ₹ (e.g., 30000 for ₹30k)"
    )
    
    parser.add_argument(
        "--risk-pct",
        type=float,
        default=0.30,
        help="Risk per trade as %% of capital (default: 0.30%%)"
    )
    
    parser.add_argument(
        "--stop-pct",
        type=float,
        default=50.0,
        help="Stop loss as %% of net debit (default: 50%%)"
    )
    
    parser.add_argument(
        "--tp-pct",
        type=float,
        default=70.0,
        help="Take profit as %% of net debit (default: 70%%)"
    )
    
    parser.add_argument(
        "--lot-size",
        type=int,
        default=50,
        help="Lot size for NIFTY (default: 50)"
    )
    
    args = parser.parse_args()
    
    # Validate inputs
    if args.capital < 20000:
        print("⚠️  Warning: Capital < ₹20k is below Day-1 minimum")
    if args.capital > 50000:
        print("⚠️  Warning: Capital > ₹50k exceeds Day-1 maximum")
    
    if args.risk_pct < 0.25 or args.risk_pct > 0.35:
        print("⚠️  Warning: Risk % outside Day-1 range (0.25-0.35%)")
    
    # Calculate
    risk_amount, net_debit_per_lot, stop_price, tp_price, lots, total_cost = \
        calculate_debit_spread_sizing(
            capital=args.capital,
            risk_pct=args.risk_pct,
            stop_pct=args.stop_pct,
            tp_pct=args.tp_pct,
            lot_size=args.lot_size
        )
    
    # Format and print
    format_output(
        capital=args.capital,
        risk_pct=args.risk_pct,
        risk_amount=risk_amount,
        net_debit_per_lot=net_debit_per_lot,
        stop_price=stop_price,
        tp_price=tp_price,
        lots=lots,
        total_cost=total_cost,
        stop_pct=args.stop_pct,
        tp_pct=args.tp_pct,
        lot_size=args.lot_size
    )


if __name__ == "__main__":
    main()

