"""
Strategy Foundry Hourly Runner.
"""
import os
import sys
import yaml
import time
import pandas as pd
import structlog
from pathlib import Path
from datetime import datetime
import pytz

# Add repo root to path for imports
sys.path.append(os.getcwd())

from packages.strategy_foundry.data.loader import DataLoader
from packages.strategy_foundry.factory.grammar import Grammar
from packages.strategy_foundry.backtest.walkforward import WalkForwardAnalyst
from packages.strategy_foundry.backtest.sanity import SanityCheck
from packages.strategy_foundry.selection.ranker import rank_candidates
from packages.strategy_foundry.selection.promote import Promoter
from packages.strategy_foundry.live.signal_publisher import SignalPublisher

logger = structlog.get_logger(__name__)

def main():
    # 1. Configuration
    config_path = "packages/strategy_foundry/configs/foundry.yaml"
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    fast_mode = os.getenv("FAST_MODE", "0") == "1"

    run_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = Path(f"packages/strategy_foundry/results/runs/{run_ts}")
    run_dir.mkdir(parents=True, exist_ok=True)

    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer()
        ]
    )

    logger.info("Starting Foundry Run", fast_mode=fast_mode, timestamp=run_ts)

    # 2. Data Loading
    loader = DataLoader()
    timeframes = config["defaults"]["timeframes"]
    symbols = config["defaults"]["symbols"]

    data_store = {}

    for sym in symbols:
        for tf in timeframes:
            try:
                # Force refresh if market is open?
                # Yes, we need latest data for signal.
                # But if we just ran an hour ago? Yahoo might not have new bars for 1D.
                # For intraday, we definitely need refresh.
                force = True
                df = loader.get_data(sym, tf, force_refresh=force)
                data_store[(sym, tf)] = df
            except Exception as e:
                logger.error("Failed to load data", symbol=sym, tf=tf, error=str(e))

    # 3. Strategy Generation & Backtest
    grammar = Grammar()
    sanity = SanityCheck(config["defaults"])

    n_candidates = config["defaults"]["candidates_per_run_fast"] if fast_mode else config["defaults"]["candidates_per_run"]

    candidates = []

    for sym in symbols:
        for tf in timeframes:
            df = data_store.get((sym, tf))
            if df is None or df.empty: continue

            # Walk-Forward Analyst
            analyst = WalkForwardAnalyst(df, n_folds=config["defaults"]["folds_fast"] if fast_mode else config["defaults"]["folds"])

            for _ in range(n_candidates):
                strategy = grammar.generate(tf)

                # Check for duplicates? Hash check?
                # Grammar gen is random, collision low with parameter space.

                # Run WFA
                try:
                    results = analyst.run(strategy)
                    if not results: continue

                    metrics = results["overall"]

                    # Sanity Check
                    passed, reasons = sanity.check_intraday(metrics, results)

                    if passed:
                        candidates.append({
                            "id": strategy.id,
                            "symbol": sym,
                            "timeframe": tf,
                            "metrics": metrics,
                            "wf_metrics": results,
                            "strategy": strategy, # Object
                            "score": 0 # Calculated later
                        })
                except Exception as e:
                    logger.warning("Backtest failed", strategy_id=strategy.id, error=str(e))

    # 4. Ranking
    ranked_df = rank_candidates(candidates)

    if not ranked_df.empty:
        # Save results
        ranked_df.to_csv(run_dir / "leaderboard.csv", index=False)

        # Markdown summary
        md_lines = ["# Strategy Foundry Leaderboard", "", f"Run: {run_ts}", ""]
        md_lines.append(ranked_df.head(10).to_markdown())
        with open(run_dir / "leaderboard.md", "w") as f:
            f.write("\n".join(md_lines))

        logger.info("Ranking complete", top_score=ranked_df.iloc[0]["score"])

        # 5. Promotion (Full Mode Only)
        if not fast_mode:
            promoter = Promoter()
            # Get top 1 across all symbols/TF?
            # Or per symbol?
            # Let's take global top 1 for now.
            top_candidate = candidates[ranked_df.index[0]] # Get original dict from list using index
            # Wait, ranked_df index might be shuffled.
            # rank_candidates returns new DF. We need to match back to candidate dict.

            # Better: rank_candidates returns DF with 'strategy' column containing the object.
            # We can reconstruct the dict.
            top_row = ranked_df.iloc[0]
            top_dict = {
                "id": top_row["id"],
                "score": top_row["score"],
                "metrics": {
                    "sharpe": top_row["sharpe"],
                    "calmar": top_row["calmar"],
                    "cagr": top_row["cagr"],
                    "max_dd": top_row["max_dd"],
                    "trades": top_row["trades"]
                    # ... add others if needed
                },
                "sharpe": top_row["sharpe"], # For promote check
                "max_dd": top_row["max_dd"],
                "strategy": top_row["strategy"] # Object
            }

            promoted = promoter.try_promote(top_dict, run_ts)

            if promoted:
                # 6. Publish Signal
                publisher = SignalPublisher()
                # Reload champion from disk to ensure we publish exactly what's stored
                champ = promoter.get_current_champion()
                if champ:
                    publisher.publish(champ)
        else:
            logger.info("Fast mode: Skipping promotion and signaling")
    else:
        logger.warning("No viable candidates found")

if __name__ == "__main__":
    main()
