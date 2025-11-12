#!/usr/bin/env python3
"""Test Iron Condor strategy on NIFTY historical data"""
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from packages.core.backtest import BacktestEngine
from packages.core.strategies.iron_condor import IronCondorStrategy


def main():
    print("="*70)
    print("🧪 IRON CONDOR BACKTEST - NIFTY Historical Data")
    print("="*70)
    print()
    
    # Iron Condor parameters
    # "9 20" interpreted as: min_dte=9, max_dte=20
    # Also using 200 point spreads (common for NIFTY)
    
    iron_condor_params = {
        "call_spread_width": 200,      # 200 point call spread
        "put_spread_width": 200,       # 200 point put spread
        "call_short_strike_offset": 200,  # Short call 200 points OTM
        "put_short_strike_offset": 200,   # Short put 200 points OTM
        "max_dte": 20,                  # Max 20 days to expiry
        "min_dte": 9,                   # Min 9 days to expiry
        "target_profit_pct": 50,        # Close at 50% profit
        "max_loss_pct": 200,            # Close at 200% loss
        "iv_percentile_min": 30,        # Min IV percentile
        "iv_percentile_max": 70,        # Max IV percentile
        "max_positions": 2              # Max 2 concurrent positions
    }
    
    print("📋 Strategy Parameters:")
    print(f"   Call Spread Width: {iron_condor_params['call_spread_width']} points")
    print(f"   Put Spread Width: {iron_condor_params['put_spread_width']} points")
    print(f"   Call Short Strike Offset: {iron_condor_params['call_short_strike_offset']} points")
    print(f"   Put Short Strike Offset: {iron_condor_params['put_short_strike_offset']} points")
    print(f"   Days to Expiry: {iron_condor_params['min_dte']} - {iron_condor_params['max_dte']}")
    print(f"   IV Percentile Range: {iron_condor_params['iv_percentile_min']} - {iron_condor_params['iv_percentile_max']}")
    print()
    
    # Initialize strategy
    strategy = IronCondorStrategy("IronCondor", iron_condor_params)
    
    # Initialize backtest engine
    initial_capital = 1000000  # 10 lakh
    engine = BacktestEngine(
        initial_capital=initial_capital,
        data_dir="docs/NSE OPINONS DATA"
    )
    
    # Date range (full available range)
    start_date = datetime(2025, 8, 15)
    end_date = datetime(2025, 11, 10)
    
    print("📅 Backtest Period:")
    print(f"   Start: {start_date.strftime('%Y-%m-%d')}")
    print(f"   End: {end_date.strftime('%Y-%m-%d')}")
    print(f"   Initial Capital: ₹{initial_capital:,.0f}")
    print()
    print("🚀 Starting backtest...")
    print()
    
    # Run backtest
    try:
        results = engine.run_backtest(
            strategies=[strategy],
            symbol="NIFTY",
            start_date=start_date,
            end_date=end_date
        )
        
        # Print results
        print("="*70)
        print("📊 BACKTEST RESULTS")
        print("="*70)
        print()
        print("💰 Capital & Returns:")
        print(f"   Initial Capital:     ₹{results['initial_capital']:,.2f}")
        print(f"   Final Capital:       ₹{results['final_capital']:,.2f}")
        print(f"   Total Return:        ₹{results['total_return']:,.2f}")
        print(f"   Total Return %:     {results['total_return_pct']:+.2f}%")
        print(f"   Max Drawdown:        {results['max_drawdown_pct']:.2f}%")
        print()
        
        print("📈 Trade Statistics:")
        print(f"   Total Trades:        {results['total_trades']}")
        print(f"   Winning Trades:     {results['wins']}")
        print(f"   Losing Trades:      {results['losses']}")
        print(f"   Win Rate:           {results['win_rate']:.2f}%")
        print()
        
        print("💵 P&L Analysis:")
        print(f"   Average Win:         ₹{results['avg_win']:,.2f}")
        print(f"   Average Loss:        ₹{results['avg_loss']:,.2f}")
        print(f"   Profit Factor:       {results['profit_factor']:.2f}")
        print(f"   Largest Win:         ₹{results['largest_win']:,.2f}")
        print(f"   Largest Loss:        ₹{results['largest_loss']:,.2f}")
        print()
        
        print("📊 Strategy Performance:")
        print(f"   Signals Generated:  {results['signals_generated']}")
        print(f"   Execution Rate:     {(results['total_trades'] / results['signals_generated'] * 100) if results['signals_generated'] > 0 else 0:.2f}%")
        print()
        
        # Performance assessment
        print("="*70)
        if results['total_return_pct'] > 0:
            print("✅ BACKTEST PROFITABLE")
        else:
            print("❌ BACKTEST SHOWS LOSSES")
        
        if results['win_rate'] >= 60:
            print("✅ Good Win Rate")
        elif results['win_rate'] >= 50:
            print("⚠️  Moderate Win Rate")
        else:
            print("❌ Low Win Rate")
        
        if results['profit_factor'] >= 2.0:
            print("✅ Excellent Profit Factor")
        elif results['profit_factor'] >= 1.5:
            print("✅ Good Profit Factor")
        elif results['profit_factor'] >= 1.0:
            print("⚠️  Marginal Profit Factor")
        else:
            print("❌ Poor Profit Factor")
        
        if results['max_drawdown_pct'] <= 10:
            print("✅ Low Drawdown")
        elif results['max_drawdown_pct'] <= 20:
            print("⚠️  Moderate Drawdown")
        else:
            print("❌ High Drawdown")
        
        print("="*70)
        print()
        
        # Show sample trades
        if engine.closed_trades:
            print("📋 Sample Trades (First 10):")
            print("-"*70)
            for i, trade in enumerate(engine.closed_trades[:10], 1):
                pnl_sign = "+" if trade['pnl'] >= 0 else ""
                print(f"{i:2d}. {trade['entry_date'].strftime('%Y-%m-%d')} → {trade['exit_date'].strftime('%Y-%m-%d')}")
                print(f"    {trade['symbol']:20s} | {trade['side']:4s} | Qty: {trade['quantity']:3d} | "
                      f"Entry: ₹{trade['entry_price']:7.2f} | Exit: ₹{trade['exit_price']:7.2f} | "
                      f"P&L: {pnl_sign}₹{trade['pnl']:8.2f} | Reason: {trade['exit_reason']}")
            print()
        
        # Recommendations
        print("💡 Recommendations:")
        if results['total_trades'] < 10:
            print("   ⚠️  Very few trades - strategy may be too selective")
            print("   → Consider widening strike offsets or IV range")
        
        if results['win_rate'] < 50 and results['total_return_pct'] < 0:
            print("   ⚠️  Low win rate with losses - review exit rules")
            print("   → Consider tighter stop losses or earlier profit taking")
        
        if results['max_drawdown_pct'] > 15:
            print("   ⚠️  High drawdown - review position sizing")
            print("   → Consider reducing per-trade risk percentage")
        
        if results['profit_factor'] < 1.0:
            print("   ⚠️  Profit factor below 1.0 - strategy losing money")
            print("   → Review strategy logic and parameters")
        
        print()
        print("📝 Next Steps:")
        print("   1. Review individual trades for patterns")
        print("   2. Test different parameter combinations")
        print("   3. Test on different date ranges (walk-forward)")
        print("   4. Paper trade if results look promising")
        print()
        
    except FileNotFoundError as e:
        print(f"❌ Error: Historical data not found")
        print(f"   {e}")
        print()
        print("💡 Make sure CSV files are in: docs/NSE OPINONS DATA/")
        return 1
    except Exception as e:
        print(f"❌ Error during backtest: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())

