"""Strategy Foundry Hourly Runner"""
import os
import sys
import argparse
import pandas as pd
import structlog
from datetime import datetime
import json
import yaml
from pathlib import Path

# Add repo root to path
sys.path.append(os.getcwd())

from packages.strategy_foundry.data.loader import DataLoader
from packages.strategy_foundry.factory.generator import StrategyGenerator
from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.backtest.walkforward import WalkForward
from packages.strategy_foundry.backtest.sanity import SanityChecker
from packages.strategy_foundry.selection.ranker import Ranker
from packages.strategy_foundry.live.signal_publisher import SignalPublisher

logger = structlog.get_logger(__name__)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fast", action="store_true", help="Run in fast mode")
    args = parser.parse_args()

    fast_mode = args.fast or os.environ.get("FAST_MODE") == "1"

    # Load config
    with open("packages/strategy_foundry/configs/foundry.yaml") as f:
        config = yaml.safe_load(f)["foundry"]

    # Setup
    loader = DataLoader()
    generator = StrategyGenerator()
    engine = BacktestEngine()
    ranker = Ranker()
    publisher = SignalPublisher()

    # Context
    symbol = "NIFTY" # Primary
    yahoo_symbol = "^NSEI"

    # 1. Update Data
    logger.info("Updating Data")
    df_5m = loader.get_data(yahoo_symbol, "5m", days=config["data_days_intraday"], force_refresh=True)
    df_15m = loader.get_data(yahoo_symbol, "15m", days=config["data_days_intraday"])
    # df_1d = loader.get_data(yahoo_symbol, "1d", days=config["data_days_daily"])

    df_5m = loader.filter_market_hours(df_5m)
    df_15m = loader.filter_market_hours(df_15m)

    if df_5m.empty:
        logger.error("No data found")
        return

    # 2. Generate Candidates
    count = config["fast_mode_candidates"] if fast_mode else config["max_candidates"]
    candidates = generator.generate(count)
    logger.info(f"Generated {len(candidates)} candidates")

    # 3. Backtest & Walkforward
    results = []

    for cand in candidates:
        # Run on 5m
        wf = WalkForward(folds=config["fast_mode_folds"] if fast_mode else config["folds"])
        splits = wf.split(df_5m)

        fold_metrics = []
        for train, test in splits:
            res = engine.run(test, cand) # Evaluate on OOS test fold
            fold_metrics.append(res["metrics"])

        # Aggregated OOS metrics
        avg_sharpe = sum(m["sharpe"] for m in fold_metrics) / len(fold_metrics)
        avg_dd = sum(m["max_dd"] for m in fold_metrics) / len(fold_metrics)
        total_trades = sum(m["trades"] for m in fold_metrics)

        metrics = fold_metrics[-1] # take last fold as representative? No, average is better for ranking
        metrics["sharpe"] = avg_sharpe
        metrics["max_dd"] = avg_dd
        metrics["trades"] = total_trades

        if SanityChecker.check_intraday(metrics, "5m"):
            results.append({
                "id": cand.get_id(),
                "config": cand,
                "timeframe": "5m",
                **metrics
            })

    # 4. Rank
    leaderboard = ranker.rank(results)

    # Save Results
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = Path(f"packages/strategy_foundry/results/runs/{ts}")
    run_dir.mkdir(parents=True, exist_ok=True)

    leaderboard.to_csv(run_dir / "leaderboard.csv")

    # 5. Promote & Publish (Only if not fast mode and we have a winner)
    if not leaderboard.empty:
        top_cand = leaderboard.iloc[0]
        logger.info("Top Candidate", id=top_cand["id"], sharpe=top_cand["sharpe"])

        # Publish Signal
        # Generate signal on LATEST data (full df)
        # Using top candidate config
        res = engine.run(df_5m, top_cand["config"])
        trades = res["trades"]

        # Determine current position from last trade or logic
        # My engine simulates trades. I need current status.
        # Engine run returns trades history. I need to know if we are currently "in" a trade.
        # Or I can look at the last few signals of the raw signal array.
        # But engine._simulate returns trades only.
        # I should expose signal generation separately or infer from equity curve/trades.

        # Quick fix: check if last trade exit_time is None (open)? My engine closes all at end of day/session.
        # "All positions flat by 15:25".
        # So at start of next hour, we are likely flat unless we are IN the session.
        # The hourly run happens during the day.
        # If I run at 10:00, I have data until 09:55.
        # I need to know if the strategy says "Buy" at 10:00.

        # The engine `run` method takes historical df.
        # To get *current* signal, I need to feed it data up to NOW.
        # The loader fetched data up to now.
        # So I just check the `entry_signals` on the last bar of `df_5m`.

        # Need to expose signals from engine
        # Refactor engine to return signals? Or just re-run parts.

        indicators = engine._calc_indicators(df_5m, top_cand["config"])
        signals = engine._generate_signals(df_5m, indicators, top_cand["config"])
        last_signal = int(signals[-1])

        publisher.publish(
            {
                "id": top_cand["id"],
                "timeframe": top_cand["timeframe"],
                "rule_summary": top_cand["config"].to_summary()
            },
            last_signal,
            symbol
        )

if __name__ == "__main__":
    main()
