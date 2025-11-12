#!/usr/bin/env python3
"""CLI script to run backtests on historical data"""
import argparse
from datetime import datetime

from packages.core.backtest import BacktestEngine
from packages.core.config import app_config
from packages.core.strategies import ORBStrategy, OptionsRankerStrategy, TrendPullbackStrategy


def main():
    parser = argparse.ArgumentParser(description="Run backtest on historical options data")
    
    parser.add_argument(
        "--symbol",
        type=str,
        choices=["NIFTY", "BANKNIFTY"],
        default="NIFTY",
        help="Underlying symbol"
    )
    
    parser.add_argument(
        "--start-date",
        type=str,
        default="2025-08-15",
        help="Start date (YYYY-MM-DD)"
    )
    
    parser.add_argument(
        "--end-date",
        type=str,
        default="2025-11-10",
        help="End date (YYYY-MM-DD)"
    )
    
    parser.add_argument(
        "--capital",
        type=float,
        default=1000000,
        help="Initial capital (default: 10 lakh)"
    )
    
    parser.add_argument(
        "--strategy",
        type=str,
        choices=["ORB", "TrendPullback", "OptionsRanker", "all"],
        default="all",
        help="Strategy to test"
    )
    
    parser.add_argument(
        "--data-dir",
        type=str,
        default="docs/NSE OPINONS DATA",
        help="Directory containing historical CSV files"
    )
    
    args = parser.parse_args()
    
    # Parse dates
    start_date = datetime.strptime(args.start_date, "%Y-%m-%d")
    end_date = datetime.strptime(args.end_date, "%Y-%m-%d")
    
    # Initialize strategies
    strategies = []
    
    if args.strategy == "all" or args.strategy == "ORB":
        orb_config = app_config.get_strategy_by_name("ORB")
        if orb_config:
            strategies.append(ORBStrategy("ORB", orb_config.params))
    
    if args.strategy == "all" or args.strategy == "TrendPullback":
        tp_config = app_config.get_strategy_by_name("TrendPullback")
        if tp_config:
            strategies.append(TrendPullbackStrategy("TrendPullback", tp_config.params))
    
    if args.strategy == "all" or args.strategy == "OptionsRanker":
        opt_config = app_config.get_strategy_by_name("OptionsRanker")
        if opt_config:
            strategies.append(OptionsRankerStrategy("OptionsRanker", opt_config.params))
    
    if not strategies:
        print("❌ No strategies configured. Check configs/app.yaml")
        return
    
    print(f"🚀 Starting backtest...")
    print(f"   Symbol: {args.symbol}")
    print(f"   Date Range: {start_date.date()} to {end_date.date()}")
    print(f"   Initial Capital: ₹{args.capital:,.0f}")
    print(f"   Strategies: {', '.join([s.name for s in strategies])}")
    print()
    
    # Run backtest
    engine = BacktestEngine(
        initial_capital=args.capital,
        data_dir=args.data_dir
    )
    
    results = engine.run_backtest(
        strategies=strategies,
        symbol=args.symbol,
        start_date=start_date,
        end_date=end_date
    )
    
    # Print results
    print("\n" + "="*60)
    print("📊 BACKTEST RESULTS")
    print("="*60)
    print(f"Initial Capital:     ₹{results['initial_capital']:,.2f}")
    print(f"Final Capital:      ₹{results['final_capital']:,.2f}")
    print(f"Total Return:       ₹{results['total_return']:,.2f} ({results['total_return_pct']:.2f}%)")
    print(f"Max Drawdown:       {results['max_drawdown_pct']:.2f}%")
    print()
    print(f"Total Trades:       {results['total_trades']}")
    print(f"Wins:               {results['wins']}")
    print(f"Losses:             {results['losses']}")
    print(f"Win Rate:           {results['win_rate']:.2f}%")
    print()
    print(f"Avg Win:            ₹{results['avg_win']:,.2f}")
    print(f"Avg Loss:           ₹{results['avg_loss']:,.2f}")
    print(f"Profit Factor:      {results['profit_factor']:.2f}")
    print()
    print(f"Largest Win:        ₹{results['largest_win']:,.2f}")
    print(f"Largest Loss:       ₹{results['largest_loss']:,.2f}")
    print()
    print(f"Signals Generated: {results['signals_generated']}")
    print("="*60)
    
    # Performance summary
    if results['total_return_pct'] > 0:
        print("✅ Backtest profitable!")
    else:
        print("❌ Backtest shows losses - review strategy parameters")
    
    print("\n💡 Tip: Review individual trades in engine.closed_trades for detailed analysis")


if __name__ == "__main__":
    main()

