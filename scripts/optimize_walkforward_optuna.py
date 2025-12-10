#!/usr/bin/env python3
"""
Walk-Forward Optimization with Optuna Integration

Combines Optuna's efficient parameter search with walk-forward validation.

Usage:
    python scripts/optimize_walkforward_optuna.py \
        --strategy MACD \
        --symbol NIFTY \
        --start-date 2025-08-15 \
        --end-date 2025-11-10 \
        --train-days 60 \
        --test-days 30 \
        --step-days 30 \
        --trials-per-window 20 \
        --output results/macd_walkforward_real.json
"""

import argparse
import sys
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from packages.core.optimization.walkforward_optuna import WalkForwardOptunaOptimizer
from packages.core.backtest import BacktestEngine
from packages.core.strategies import MACDStrategy
import structlog

logger = structlog.get_logger(__name__)


def create_backtest_function(strategy_name: str, symbol: str):
    """Create a backtest function for walk-forward optimization"""
    
    def backtest_with_params(params: dict, start_date: datetime, end_date: datetime):
        """Run backtest with given parameters and date range"""
        # Create strategy with parameters
        strategy = MACDStrategy(strategy_name, params)
        
        # Run backtest
        engine = BacktestEngine(
            initial_capital=1000000.0,
            data_dir="docs/NSE OPINONS DATA"
        )
        
        results = engine.run_backtest(
            strategies=[strategy],
            symbol=symbol,
            start_date=start_date,
            end_date=end_date
        )
        
        # Extract metrics
        if results and len(results) > 0:
            result = results[0]
            return {
                'sharpe_ratio': result.get('sharpe_ratio', 0.0),
                'total_return': result.get('total_return', 0.0),
                'win_rate': result.get('win_rate', 0.0),
                'max_drawdown': result.get('max_drawdown', 0.0),
                'trades': result.get('trades', [])
            }
        else:
            return {
                'sharpe_ratio': 0.0,
                'total_return': 0.0,
                'win_rate': 0.0,
                'max_drawdown': 0.0,
                'trades': []
            }
    
    return backtest_with_params


def main():
    parser = argparse.ArgumentParser(
        description="Walk-forward optimization with Optuna integration"
    )
    parser.add_argument("--strategy", required=True, help="Strategy name (e.g., MACD)")
    parser.add_argument("--symbol", required=True, help="Symbol (e.g., NIFTY)")
    parser.add_argument("--start-date", required=True, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", required=True, help="End date (YYYY-MM-DD)")
    parser.add_argument("--train-days", type=int, default=60, help="Training period (days)")
    parser.add_argument("--test-days", type=int, default=30, help="Test period (days)")
    parser.add_argument("--step-days", type=int, default=30, help="Step size (days)")
    parser.add_argument("--trials-per-window", type=int, default=50, help="Optuna trials per window")
    parser.add_argument("--output", help="Output JSON file for results")
    
    args = parser.parse_args()
    
    # Parse dates
    start_date = datetime.strptime(args.start_date, "%Y-%m-%d")
    end_date = datetime.strptime(args.end_date, "%Y-%m-%d")
    
    # Define parameter space (example for MACD)
    parameter_space = {
        'macd_fast': {'type': 'int', 'low': 8, 'high': 16},
        'macd_slow': {'type': 'int', 'low': 20, 'high': 30},
        'macd_signal': {'type': 'int', 'low': 6, 'high': 12},
        'rsi_period': {'type': 'int', 'low': 10, 'high': 20},
        'rsi_min': {'type': 'int', 'low': 25, 'high': 35},
        'rsi_max': {'type': 'int', 'low': 65, 'high': 75}
    }
    
    # Create backtest function
    backtest_fn = create_backtest_function(args.strategy, args.symbol)
    
    # Initialize walk-forward optimizer
    optimizer = WalkForwardOptunaOptimizer(
        strategy_name=args.strategy,
        backtest_function=backtest_fn,
        objective_metric="sharpe_ratio",
        train_period_days=args.train_days,
        test_period_days=args.test_days,
        step_days=args.step_days
    )
    
    logger.info(
        "Starting walk-forward optimization",
        strategy=args.strategy,
        symbol=args.symbol,
        start_date=args.start_date,
        end_date=args.end_date,
        train_days=args.train_days,
        test_days=args.test_days
    )
    
    # Run optimization
    results = optimizer.optimize(
        start_date=start_date,
        end_date=end_date,
        parameter_space=parameter_space,
        n_trials_per_window=args.trials_per_window
    )
    
    # Save results
    output_file = args.output or f"results/{args.strategy}_walkforward_{args.symbol}.json"
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    logger.info("Walk-forward optimization complete", output_file=output_file)
    print(f"\n✅ Results saved to: {output_file}")
    print(f"\n📊 Summary:")
    print(f"   Windows: {len(results.get('windows', []))}")
    print(f"   OOS Sharpe Mean: {results.get('oos_metrics', {}).get('sharpe_mean', 0.0):.4f}")
    print(f"   PBO: {results.get('pbo', 0.0):.2%}")


if __name__ == "__main__":
    main()
