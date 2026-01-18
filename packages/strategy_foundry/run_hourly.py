import os
import sys
import pandas as pd
import logging
from datetime import datetime
import pytz

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("FoundryRunner")

from packages.strategy_foundry.data.loader import DataLoader
from packages.strategy_foundry.factory.generator import StrategyGenerator
from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.backtest.walkforward import WalkForwardEvaluator
from packages.strategy_foundry.backtest.sanity import check_sanity
from packages.strategy_foundry.selection.ranker import Ranker
from packages.strategy_foundry.selection.champion_store import ChampionStore
from packages.strategy_foundry.live.signal_publisher import SignalPublisher

def main():
    # 1. Config
    fast_mode = os.environ.get("FAST_MODE", "0") == "1"
    n_candidates = 15 if fast_mode else 80
    n_folds = 2 if fast_mode else 4

    logger.info(f"Starting Foundry Run. FastMode={fast_mode}, N={n_candidates}, Folds={n_folds}")

    run_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_dir = f"packages/strategy_foundry/results/runs/{run_ts}"
    os.makedirs(results_dir, exist_ok=True)

    # 2. Data
    loader = DataLoader()
    # Fetch NIFTY 15m and 5m
    logger.info("Fetching data...")
    df_15m = loader.fetch_data("NIFTY", "15m", force_refresh=True)
    df_5m = loader.fetch_data("NIFTY", "5m", force_refresh=True)
    df_1d = loader.fetch_data("NIFTY", "1d", force_refresh=True) # For sanity check

    # 3. Generate
    generator = StrategyGenerator()
    candidates = generator.generate_candidates(n_candidates)
    logger.info(f"Generated {len(candidates)} candidates.")

    # 4. Evaluate
    engine = BacktestEngine()
    evaluator = WalkForwardEvaluator(engine)
    ranker = Ranker()

    results = []

    for i, spec in enumerate(candidates):
        if i % 10 == 0: logger.info(f"Processing {i}/{len(candidates)}")

        # 15m Run
        metrics_15m = evaluator.evaluate(df_15m, spec, folds=n_folds) if not df_15m.empty else {}
        # Use returned sanity or default
        sanity_15m = metrics_15m.get("sanity", {"late_day_dependence": True, "min_trades": False, "overtrade": True})

        # Ensure min trades check uses updated metrics
        sanity_15m["min_trades"] = metrics_15m.get("total_trades", 0) >= (40 if fast_mode else 40)

        score_15m = ranker.score_candidate(metrics_15m, sanity_15m) if metrics_15m else 0

        # 5m Run
        metrics_5m = evaluator.evaluate(df_5m, spec, folds=n_folds) if not df_5m.empty else {}
        sanity_5m = metrics_5m.get("sanity", {"late_day_dependence": True, "min_trades": False, "overtrade": True})

        sanity_5m["min_trades"] = metrics_5m.get("total_trades", 0) >= (80 if fast_mode else 80)

        score_5m = ranker.score_candidate(metrics_5m, sanity_5m) if metrics_5m else 0

        # Blend
        final_score = ranker.blend_scores(score_15m, score_5m)

        is_eligible = ranker.is_eligible(metrics_15m, metrics_5m, sanity_15m, sanity_5m)

        results.append({
            "spec": spec,
            "metrics_15m": metrics_15m,
            "score_15m": score_15m,
            "metrics_5m": metrics_5m,
            "score_5m": score_5m,
            "final_score": final_score,
            "eligible": is_eligible
        })

    # 5. Rank
    results.sort(key=lambda x: x["final_score"], reverse=True)

    # 6. Daily Sanity Overlay (Top 10)
    if not df_1d.empty:
        logger.info("Running 1D Sanity Check on Top 10...")
        top_n = min(len(results), 10)
        for i in range(top_n):
            res = results[i]
            if not res["eligible"]: continue

            # Run 1D Backtest (Full, no WFE needed as it's sanity)
            run_res_1d = engine.run(df_1d, res["spec"])
            m_1d = run_res_1d["metrics"]

            # Penalize if catastrophically negative
            # Sharpe < -0.2 or MaxDD > 45%
            if m_1d["sharpe"] < -0.2 or m_1d["max_dd"] > 0.45:
                logger.warning(f"Candidate {res['spec']['id']} failed 1D sanity. Sharpe={m_1d['sharpe']:.2f}, MaxDD={m_1d['max_dd']:.2f}")
                res["final_score"] -= 50 # Penalty
                res["eligible"] = False # Disqualify
                res["failed_1d"] = True
            else:
                res["failed_1d"] = False

        # Re-sort after penalties
        results.sort(key=lambda x: x["final_score"], reverse=True)

    # Save Metrics CSV
    csv_data = []
    for r in results:
        row = {
            "id": r["spec"]["id"],
            "score": r["final_score"],
            "eligible": r["eligible"],
            "sharpe_15m": r["metrics_15m"].get("sharpe", 0),
            "trades_15m": r["metrics_15m"].get("total_trades", 0),
            "sharpe_5m": r["metrics_5m"].get("sharpe", 0),
            "trades_5m": r["metrics_5m"].get("total_trades", 0),
            "strategy_type": r["spec"]["strategy_type"],
            "failed_1d": r.get("failed_1d", False)
        }
        csv_data.append(row)

    pd.DataFrame(csv_data).to_csv(f"{results_dir}/metrics.csv", index=False)

    # 7. Champion Selection
    store = ChampionStore()
    if results:
        top_candidate = results[0]
        logger.info(f"Top Candidate: {top_candidate['spec']['id']} Score: {top_candidate['final_score']}")

        if top_candidate["eligible"]:
            # Check Promotion
            combined_metrics = {
                "15m": top_candidate["metrics_15m"],
                "5m": top_candidate["metrics_5m"]
            }
            if store.should_promote(top_candidate["final_score"], combined_metrics):
                logger.info("Promoting new Champion!")
                store.save_new_champion(
                    top_candidate["spec"],
                    combined_metrics,
                    top_candidate["final_score"],
                    run_ts
                )
            else:
                logger.info("Top candidate did not beat current champion.")
        else:
            logger.info("Top candidate not eligible for champion status.")

    # 8. Publish Signal
    if not fast_mode:
        publisher = SignalPublisher()
        publisher.publish()
        logger.info("Signal publication step completed.")
    else:
        logger.info("Skipping signal publication in FAST_MODE")

if __name__ == "__main__":
    main()
