"""Main Hourly Runner"""
import os
import sys
import structlog
import pandas as pd
from datetime import datetime
import yaml

# Ensure pythonpath
sys.path.append(os.getcwd())

from packages.strategy_foundry.data.loader import DataLoader
from packages.strategy_foundry.factory.generator import StrategyGenerator
from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.backtest.walkforward import WalkForward
from packages.strategy_foundry.selection.ranker import Ranker, ChampionStore
from packages.strategy_foundry.selection.promote import Promoter
from packages.strategy_foundry.live.signal_publisher import SignalPublisher
from packages.strategy_foundry.backtest.sanity import sanity_check_candidate, daily_sanity_overlay

logger = structlog.get_logger(__name__)

def run():
    # 1. Config
    fast_mode = os.environ.get("FAST_MODE", "0") == "1"
    logger.info("Starting Hourly Run", fast_mode=fast_mode)

    loader = DataLoader()
    generator = StrategyGenerator()
    ranker = Ranker()
    promoter = Promoter()
    store = ChampionStore()

    # 2. Data Update
    timeframes = ["5m", "15m"]
    symbols = ["NIFTY"] # Focus on Nifty

    datasets = {}
    daily_data = None

    for s in symbols:
        # Load Daily for Sanity
        daily_data = loader.get_data(s, "1D")

        for tf in timeframes:
            df = loader.get_data(s, tf)
            if not df.empty:
                datasets[(s, tf)] = df

    if not datasets:
        logger.error("No data available")
        return

    # 3. Generate Candidates
    num_candidates = 15 if fast_mode else 80
    candidates = generator.generate(num_candidates)

    # 4. Backtest & Eval
    results = []

    for cand in candidates:
        for (sym, tf), df in datasets.items():
            # Walk Forward
            wf = WalkForward(df, folds=2 if fast_mode else 4)
            wf_res = wf.run(cand)

            metrics = wf_res["full_result"] # Using full result for ranking for now, but gating on folds

            # Additional WF Metrics
            metrics["consistency"] = wf_res["consistency"]
            metrics["avg_sharpe_folds"] = wf_res["avg_sharpe"]

            # Sanity Check
            if not sanity_check_candidate(metrics, fast_mode):
                continue

            # Daily Sanity Overlay (Top candidates only? Or all? fast enough for all here)
            if not daily_sanity_overlay(BacktestEngine, cand, daily_data):
                continue

            res_entry = metrics.copy()
            res_entry["id"] = cand.id
            res_entry["symbol"] = sym
            res_entry["timeframe"] = tf
            res_entry["candidate_obj"] = cand
            results.append(res_entry)

    # 5. Rank
    if not results:
        logger.warning("No viable candidates found")
        return

    ranked_df = ranker.rank(results, "blended")

    # Save Leaderboard
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = f"packages/strategy_foundry/results/runs/{ts}"
    os.makedirs(out_dir, exist_ok=True)

    ranked_df_drop = ranked_df.drop(columns=["candidate_obj"])
    ranked_df_drop.to_csv(f"{out_dir}/leaderboard.csv")

    # 6. Promote
    if not fast_mode and not ranked_df.empty:
        top = ranked_df.iloc[0]
        cand_obj = [r["candidate_obj"] for r in results if r["id"] == top["id"]][0]

        # Convert row to dict
        metrics = top.to_dict()

        if promoter.check_promotion(metrics, cand_obj.to_dict()):
            logger.info("New Champion Promoted", id=top["id"], score=top["score"])
            store.save_champion(cand_obj.to_dict(), metrics, top["timeframe"])
        else:
            logger.info("Champion retained")

    # 7. Publish Signal
    publisher = SignalPublisher()
    publisher.publish()

if __name__ == "__main__":
    run()
