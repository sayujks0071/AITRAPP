"""Canonical Runner for Strategy Execution (Backtest, Paper, Live)"""
import argparse
import asyncio
import os
import signal
import sys
from datetime import datetime, timedelta
from typing import List, Optional

import structlog

from packages.core.backtest import BacktestEngine
from packages.core.config import app_config, AppMode
from packages.core.strategies import ORBStrategy, OptionsRankerStrategy, TrendPullbackStrategy
from packages.core.paper_simulator import PaperSimulator
from packages.core.models import Instrument, Tick, Bar, Signal, SignalSide
from packages.core.strategies.base import StrategyContext

logger = structlog.get_logger(__name__)

class Runner:
    """
    Canonical runner for executing strategies in different modes.
    """

    def __init__(self, mode: str, strategy_name: str, symbol: str, data_dir: Optional[str] = None):
        self.mode = mode
        self.strategy_name = strategy_name
        self.symbol = symbol
        self.data_dir = data_dir or "docs/NSE OPINONS DATA"
        self.strategies = self._load_strategies(strategy_name)

        if not self.strategies:
            logger.error("No strategies loaded. Exiting.")
            sys.exit(1)

    def _load_strategies(self, strategy_name: str):
        strategies = []
        if strategy_name == "all" or strategy_name == "ORB":
            orb_config = app_config.get_strategy_by_name("ORB")
            if orb_config:
                strategies.append(ORBStrategy("ORB", orb_config.params))

        if strategy_name == "all" or strategy_name == "TrendPullback":
            tp_config = app_config.get_strategy_by_name("TrendPullback")
            if tp_config:
                strategies.append(TrendPullbackStrategy("TrendPullback", tp_config.params))

        if strategy_name == "all" or strategy_name == "OptionsRanker":
            opt_config = app_config.get_strategy_by_name("OptionsRanker")
            if opt_config:
                strategies.append(OptionsRankerStrategy("OptionsRanker", opt_config.params))
        return strategies

    def run_backtest(self, start_date: str, end_date: str, capital: float):
        """Run backtest engine"""
        logger.info("Starting Backtest", strategy=self.strategy_name, symbol=self.symbol)

        s_date = datetime.strptime(start_date, "%Y-%m-%d")
        e_date = datetime.strptime(end_date, "%Y-%m-%d")

        engine = BacktestEngine(
            initial_capital=capital,
            data_dir=self.data_dir
        )

        results = engine.run_backtest(
            strategies=self.strategies,
            symbol=self.symbol,
            start_date=s_date,
            end_date=e_date
        )

        self._print_backtest_summary(results)
        return results

    def _print_backtest_summary(self, results):
        print("\n" + "="*60)
        print("📊 BACKTEST RESULTS")
        print("="*60)
        print(f"Total Return:       ₹{results['total_return']:,.2f} ({results['total_return_pct']:.2f}%)")
        print(f"Total Trades:       {results['total_trades']}")
        print(f"Win Rate:           {results['win_rate']:.2f}%")
        print("="*60)

    async def run_paper_local(self, minutes: float = 10, interval_sec: int = 1):
        """
        Run paper trading simulation loop in-process.

        This bypasses the API server and Orchestrator, running strategies directly
        against a simulated feed and execution engine.
        """
        logger.info("Starting Paper-Local Simulation", duration_minutes=minutes)

        # Initialize Simulator
        paper_sim = PaperSimulator(
            slippage_bps=app_config.risk.slippage_bps,
            fees_per_order=app_config.risk.fees_per_order
        )

        positions = []
        end_time = datetime.now() + timedelta(minutes=minutes)

        # Mock instrument for simulation
        mock_instrument = Instrument(
            token=123456,
            symbol=self.symbol,
            tradingsymbol=f"{self.symbol}25SEP25000CE",
            exchange="NFO",
            instrument_type="CE", # Simplified
            strike=25000,
            lot_size=50,
            tick_size=0.05
        )

        # Simulation Loop
        print(f"Simulating market data for {minutes} minutes...")

        current_price = 100.0

        while datetime.now() < end_time:
            # 1. Generate Tick (Random Walk for simulation)
            import random
            change = random.uniform(-0.5, 0.5)
            current_price += change

            tick = Tick(
                token=mock_instrument.token,
                timestamp=datetime.now(),
                last_price=current_price,
                last_quantity=1,
                volume=100,
                open=100,
                high=max(100, current_price),
                low=min(100, current_price),
                close=current_price,
                oi=5000
            )

            # 2. Build Context
            context = StrategyContext(
                timestamp=datetime.now(),
                instrument=mock_instrument,
                latest_tick=tick,
                bars_5s=[], # Simplified: Empty bars for now
                bars_1s=[],
                net_liquid=1000000.0,
                available_margin=800000.0,
                open_positions=len([p for p in positions if p.is_open])
            )

            # 3. Evaluate Strategies
            for strategy in self.strategies:
                signals = strategy.generate_signals(context)

                for signal in signals:
                    logger.info(f"Signal Generated: {signal.side} {signal.instrument.tradingsymbol} @ {signal.entry_price}")

                    # 4. Execute Signal (Immediate Fill for Paper)
                    order = paper_sim.simulate_order(
                        instrument_token=signal.instrument.token,
                        instrument_symbol=signal.instrument.tradingsymbol,
                        side="BUY" if signal.side == SignalSide.LONG else "SELL",
                        quantity=50, # Fixed qty for simplicity
                        order_type="MARKET",
                        current_market_price=current_price
                    )

                    position = paper_sim.open_position(
                        signal.instrument,
                        order,
                        signal.side,
                        signal.stop_loss,
                        signal.take_profit_1,
                        signal.take_profit_2
                    )
                    positions.append(position)
                    strategy.on_position_opened()
                    print(f"Executed: {order.side} {order.quantity} @ {order.average_price:.2f}")

            # 5. Update Positions & Check Exits
            for pos in positions:
                if pos.is_open:
                    pos.current_price = current_price
                    pos.update_pnl()

                    # Simple SL/TP check
                    if pos.unrealized_pnl < -500 or pos.unrealized_pnl > 1000:
                         # Close
                         exit_order = paper_sim.close_position(pos, current_price, "TP_SL")
                         print(f"Closed: {pos.instrument.tradingsymbol} PnL: {pos.realized_pnl:.2f}")

            await asyncio.sleep(interval_sec)

        print("\nSimulation Complete.")
        print(f"Total Positions: {len(positions)}")
        total_pnl = sum([p.realized_pnl or 0.0 for p in positions]) + sum([p.unrealized_pnl for p in positions if p.is_open])
        print(f"Total PnL: {total_pnl:.2f}")

    def run_live(self):
        """Run in Live Mode (Gated)"""
        if os.environ.get("TRADING_MODE") != "live" or os.environ.get("I_UNDERSTAND_LIVE_TRADING") != "true":
            logger.error("❌ LIVE MODE REFUSED. Missing safety flags.")
            print("To run in live mode, you must set:")
            print("  export TRADING_MODE=live")
            print("  export I_UNDERSTAND_LIVE_TRADING=true")
            sys.exit(1)

        logger.info("⚠️ STARTING LIVE TRADING MODE ⚠️")
        logger.warning("Real orders will be placed. Press Ctrl+C to abort in 5 seconds...")
        import time
        try:
            time.sleep(5)
        except KeyboardInterrupt:
            print("\nAborted.")
            sys.exit(0)

        # For now, we just print a placeholder as instructed not to place real orders
        logger.info("Live engine starting... (Safety: No real orders in this PR)")
        # In future, this would instantiate the Orchestrator with a LiveBroker.

def main():
    parser = argparse.ArgumentParser(description="Kite Strategy Runner")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Common args
    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument("--strategy", type=str, default="ORB", help="Strategy name (ORB, TrendPullback, etc.)")
    common_parser.add_argument("--symbol", type=str, default="NIFTY", help="Symbol (NIFTY, BANKNIFTY)")
    common_parser.add_argument("--data-dir", type=str, help="Path to data directory")

    # Backtest
    bt_parser = subparsers.add_parser("backtest", parents=[common_parser], help="Run backtest")
    bt_parser.add_argument("--start-date", type=str, default="2025-08-15")
    bt_parser.add_argument("--end-date", type=str, default="2025-11-10")
    bt_parser.add_argument("--capital", type=float, default=1000000)

    # Paper Local
    paper_parser = subparsers.add_parser("paper-local", parents=[common_parser], help="Run local paper simulation")
    paper_parser.add_argument("--minutes", type=float, default=1.0, help="Duration in minutes")

    # Live
    live_parser = subparsers.add_parser("live", parents=[common_parser], help="Run live trading (GATED)")

    args = parser.parse_args()

    runner = Runner(args.command, args.strategy, args.symbol, args.data_dir)

    if args.command == "backtest":
        runner.run_backtest(args.start_date, args.end_date, args.capital)
    elif args.command == "paper-local":
        asyncio.run(runner.run_paper_local(args.minutes))
    elif args.command == "live":
        runner.run_live()

if __name__ == "__main__":
    main()
