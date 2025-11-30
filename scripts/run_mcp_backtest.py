#!/usr/bin/env python3
"""
MCP-Powered Backtest Runner
============================

Runs backtests using real historical data from Kite Connect via MCP.

Features:
1. Fetch real market data from Kite
2. Replay through strategies
3. Generate performance metrics
4. Compare strategy performance
5. Export results

Usage:
    # Backtest single strategy for last 7 days
    python scripts/run_mcp_backtest.py --strategy RSIMeanReversion --days 7

    # Backtest multiple strategies
    python scripts/run_mcp_backtest.py --strategy "RSIMeanReversion,MACD,BollingerBands" --days 14

    # Specific date range
    python scripts/run_mcp_backtest.py --from-date "2025-11-20" --to-date "2025-11-26"

    # Paper trading replay mode (simulate today's trading)
    python scripts/run_mcp_backtest.py --replay-mode --interval 1minute
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

import structlog

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from packages.core.config import load_config
from packages.core.historical_data_mcp import HistoricalDataMCPProvider
from packages.core.hivemind.kite_mcp_adapter import KiteMCPAdapter
from packages.core.hivemind.mcp_client import MCPClient
from packages.core.indicators import IndicatorCalculator
from packages.core.models import Bar, Instrument, InstrumentType
from packages.core.strategies import get_strategy_by_name

logger = structlog.get_logger(__name__)


class MCPBacktestRunner:
    """
    Backtest runner using real historical data from Kite MCP.
    """

    def __init__(self, mcp_url: str = "http://localhost:8080"):
        """
        Initialize the backtest runner.

        Args:
            mcp_url: MCP server URL
        """
        self.mcp_client = MCPClient(server_url=mcp_url)
        self.adapter = KiteMCPAdapter(mcp_client=self.mcp_client)
        self.provider = HistoricalDataMCPProvider(kite_mcp_adapter=self.adapter)

        # State
        self.capital = 1000000  # 10 lakh
        self.positions = []
        self.trades = []
        self.signals_log = []

        logger.info("🚀 MCPBacktestRunner initialized", mcp_url=mcp_url)

    def search_options_chain(
        self, underlying: str, expiry: str = None, strikes: int = 10
    ) -> List[Instrument]:
        """
        Search for options instruments.

        Args:
            underlying: Underlying symbol (e.g., "NIFTY")
            expiry: Expiry date (optional, defaults to nearest)
            strikes: Number of ATM strikes to fetch

        Returns:
            List of Instrument objects
        """
        logger.info(f"Searching options chain for {underlying}")

        # Search for options
        instruments = self.provider.search_instrument(f"NFO:{underlying}")

        # Filter to options only
        options = [
            inst for inst in instruments
            if inst.get("instrument_type") in ["CE", "PE"]
        ]

        logger.info(f"Found {len(options)} options for {underlying}")

        # Convert to Instrument objects
        result = []
        for opt in options[:strikes * 2]:  # CE + PE
            inst = Instrument(
                token=opt["instrument_token"],
                exchange=opt["exchange"],
                tradingsymbol=opt["tradingsymbol"],
                name=opt.get("name", opt["tradingsymbol"]),
                instrument_type=InstrumentType.from_string(opt["instrument_type"]),
                strike=opt.get("strike", 0),
                expiry=datetime.fromisoformat(opt["expiry"]) if "expiry" in opt else None,
                lot_size=opt.get("lot_size", 1)
            )
            result.append(inst)

        return result

    def run_backtest(
        self,
        strategies: List[str],
        from_date: datetime,
        to_date: datetime,
        underlying: str = "NIFTY",
        interval: str = "5minute",
        initial_capital: float = 1000000
    ) -> Dict:
        """
        Run backtest using MCP historical data.

        Args:
            strategies: List of strategy names
            from_date: Start date
            to_date: End date
            underlying: Underlying symbol
            interval: Candle interval
            initial_capital: Starting capital

        Returns:
            Backtest results dictionary
        """
        logger.info(
            "🎯 Starting MCP backtest",
            strategies=strategies,
            from_date=from_date,
            to_date=to_date,
            underlying=underlying
        )

        self.capital = initial_capital

        # 1. Search for instruments
        instruments = self.search_options_chain(underlying, strikes=5)
        logger.info(f"Testing {len(instruments)} instruments")

        # 2. Fetch historical data for all instruments
        logger.info(f"Fetching historical data from {from_date} to {to_date}")

        bars_by_instrument = self.provider.fetch_multiple_instruments(
            instruments=instruments,
            from_date=from_date,
            to_date=to_date,
            interval=interval
        )

        total_bars = sum(len(bars) for bars in bars_by_instrument.values())
        logger.info(f"Fetched {total_bars} total bars across {len(instruments)} instruments")

        # 3. Initialize strategies
        strategy_instances = []
        for strategy_name in strategies:
            try:
                strategy = get_strategy_by_name(strategy_name)
                if strategy:
                    strategy_instances.append(strategy)
                    logger.info(f"✅ Loaded strategy: {strategy_name}")
            except Exception as e:
                logger.error(f"Failed to load strategy {strategy_name}: {e}")

        if not strategy_instances:
            logger.error("No strategies loaded!")
            return {}

        # 4. Replay bars through strategies
        logger.info("🔄 Replaying historical data...")

        # Get all unique timestamps
        all_timestamps = set()
        for bars in bars_by_instrument.values():
            all_timestamps.update(bar.timestamp for bar in bars)

        sorted_timestamps = sorted(all_timestamps)
        logger.info(f"Processing {len(sorted_timestamps)} unique timestamps")

        # Replay tick by tick
        for idx, timestamp in enumerate(sorted_timestamps):
            # Get all bars at this timestamp
            current_bars = []
            for inst_token, bars in bars_by_instrument.items():
                matching_bars = [b for b in bars if b.timestamp == timestamp]
                current_bars.extend(matching_bars)

            # Feed to strategies
            for strategy in strategy_instances:
                for bar in current_bars:
                    try:
                        # Calculate indicators
                        indicators = self._calculate_indicators(bar, bars_by_instrument[bar.instrument.token])

                        # Generate signals
                        signal = strategy.scan(bar, indicators)

                        if signal:
                            self.signals_log.append({
                                "timestamp": timestamp,
                                "strategy": strategy.__class__.__name__,
                                "signal": signal.side.value,
                                "instrument": bar.instrument.tradingsymbol,
                                "price": bar.close
                            })

                            # Simulate order execution
                            self._execute_signal(signal, bar)

                    except Exception as e:
                        logger.debug(f"Strategy error: {e}")

            # Progress update
            if idx % 100 == 0:
                pct = (idx / len(sorted_timestamps)) * 100
                logger.info(f"Progress: {pct:.1f}% ({idx}/{len(sorted_timestamps)})")

        # 5. Calculate results
        results = self._calculate_results(strategy_instances)

        logger.info(
            "✅ Backtest complete",
            total_signals=len(self.signals_log),
            total_trades=len(self.trades),
            final_capital=results.get("final_capital", 0)
        )

        return results

    def _calculate_indicators(self, bar: Bar, all_bars: List[Bar]) -> Dict:
        """Calculate technical indicators for a bar."""
        calc = IndicatorCalculator()

        # Need at least 50 bars for most indicators
        if len(all_bars) < 50:
            return {}

        recent_bars = all_bars[-50:]

        try:
            closes = [b.close for b in recent_bars]
            highs = [b.high for b in recent_bars]
            lows = [b.low for b in recent_bars]

            return {
                "rsi": calc.calculate_rsi(closes, period=14),
                "atr": calc.calculate_atr(highs, lows, closes, period=14),
                "macd": calc.calculate_macd(closes),
                "bb_upper": calc.calculate_bollinger_upper(closes),
                "bb_lower": calc.calculate_bollinger_lower(closes)
            }
        except Exception as e:
            logger.debug(f"Indicator calculation error: {e}")
            return {}

    def _execute_signal(self, signal, bar):
        """Simulate order execution."""
        # Simplified execution simulation
        self.trades.append({
            "timestamp": bar.timestamp,
            "instrument": bar.instrument.tradingsymbol,
            "side": signal.side.value,
            "price": bar.close,
            "size": signal.size
        })

    def _calculate_results(self, strategies: List) -> Dict:
        """Calculate backtest performance metrics."""
        total_signals = len(self.signals_log)
        total_trades = len(self.trades)

        # Group signals by strategy
        signals_by_strategy = {}
        for signal in self.signals_log:
            strategy_name = signal["strategy"]
            if strategy_name not in signals_by_strategy:
                signals_by_strategy[strategy_name] = 0
            signals_by_strategy[strategy_name] += 1

        return {
            "total_signals": total_signals,
            "total_trades": total_trades,
            "signals_by_strategy": signals_by_strategy,
            "final_capital": self.capital,
            "strategies_tested": [s.__class__.__name__ for s in strategies]
        }

    def replay_live_mode(
        self,
        strategies: List[str],
        underlying: str = "NIFTY",
        interval: str = "1minute"
    ):
        """
        Replay today's market for paper trading simulation.

        Args:
            strategies: List of strategy names
            underlying: Underlying symbol
            interval: Replay interval (1minute for high fidelity)
        """
        logger.info("📡 Starting live replay mode")

        # Get today's data
        today = datetime.now().replace(hour=9, minute=15, second=0, microsecond=0)
        now = datetime.now()

        # If after market close, use full day
        if now.hour >= 16:
            end_time = today.replace(hour=15, minute=30)
        else:
            end_time = now

        logger.info(f"Replaying from {today} to {end_time}")

        # Run backtest on today's data
        results = self.run_backtest(
            strategies=strategies,
            from_date=today,
            to_date=end_time,
            underlying=underlying,
            interval=interval
        )

        logger.info("📊 Replay complete", results=results)
        return results


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="MCP-powered backtest runner")

    parser.add_argument(
        "--strategy",
        type=str,
        default="RSIMeanReversion",
        help="Strategy name(s), comma-separated"
    )

    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Number of days to backtest (default: 7)"
    )

    parser.add_argument(
        "--from-date",
        type=str,
        help="Start date (YYYY-MM-DD)"
    )

    parser.add_argument(
        "--to-date",
        type=str,
        help="End date (YYYY-MM-DD)"
    )

    parser.add_argument(
        "--underlying",
        type=str,
        default="NIFTY",
        help="Underlying symbol (default: NIFTY)"
    )

    parser.add_argument(
        "--interval",
        type=str,
        default="5minute",
        choices=["1minute", "3minute", "5minute", "15minute", "30minute", "60minute", "day"],
        help="Candle interval (default: 5minute)"
    )

    parser.add_argument(
        "--replay-mode",
        action="store_true",
        help="Replay today's market for paper trading simulation"
    )

    parser.add_argument(
        "--capital",
        type=float,
        default=1000000,
        help="Initial capital (default: 1000000)"
    )

    parser.add_argument(
        "--mcp-url",
        type=str,
        default="http://localhost:8080",
        help="MCP server URL (default: http://localhost:8080)"
    )

    parser.add_argument(
        "--output",
        type=str,
        help="Output JSON file for results"
    )

    args = parser.parse_args()

    # Parse strategies
    strategies = [s.strip() for s in args.strategy.split(",")]

    # Initialize runner
    runner = MCPBacktestRunner(mcp_url=args.mcp_url)

    # Determine date range
    if args.replay_mode:
        # Replay mode - today's data
        logger.info("🎬 Running in REPLAY mode - simulating today's trading")
        results = runner.replay_live_mode(
            strategies=strategies,
            underlying=args.underlying,
            interval=args.interval
        )

    else:
        # Backtest mode
        if args.from_date and args.to_date:
            from_date = datetime.strptime(args.from_date, "%Y-%m-%d")
            to_date = datetime.strptime(args.to_date, "%Y-%m-%d")
        else:
            to_date = datetime.now()
            from_date = to_date - timedelta(days=args.days)

        # Run backtest
        results = runner.run_backtest(
            strategies=strategies,
            from_date=from_date,
            to_date=to_date,
            underlying=args.underlying,
            interval=args.interval,
            initial_capital=args.capital
        )

    # Print results
    print("\n" + "=" * 60)
    print("📊 BACKTEST RESULTS")
    print("=" * 60)
    print(json.dumps(results, indent=2, default=str))
    print("=" * 60 + "\n")

    # Save to file if requested
    if args.output:
        output_path = Path(args.output)
        output_path.write_text(json.dumps(results, indent=2, default=str))
        logger.info(f"Results saved to {output_path}")


if __name__ == "__main__":
    main()
