import os
import sys
import argparse
import pandas as pd
import structlog
from datetime import datetime

# Setup paths
sys.path.append(os.getcwd())

from packages.strategy_foundry.data.loader import get_historical_data
from packages.strategy_foundry.factory.generator import StrategyGenerator, GeneratedStrategy
from packages.strategy_foundry.backtest.engine import FoundryEngine
from packages.strategy_foundry.backtest.walkforward import WalkForward
from packages.strategy_foundry.backtest.sanity import check_sanity
from packages.strategy_foundry.selection.ranker import Ranker
from packages.strategy_foundry.selection.champion_store import load_champion, save_champion
from packages.strategy_foundry.selection.promote import should_promote
from packages.strategy_foundry.live.signal_publisher import publish_signal

logger = structlog.get_logger(__name__)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fast", action="store_true", help="Run in fast mode")
    args = parser.parse_args()

    fast_mode = args.fast or os.environ.get("FAST_MODE") == "1"

    run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = f"packages/strategy_foundry/results/runs/{run_timestamp}"
    os.makedirs(run_dir, exist_ok=True)

    logger.info("Starting Foundry Run", fast_mode=fast_mode, run_dir=run_dir)

    # 1. Data
    try:
        df_nifty = get_historical_data("NIFTY")
    except Exception as e:
        logger.error("Failed to load data", error=str(e))
        return

    # 2. Generate
    n_candidates = 10 if fast_mode else 50
    gen = StrategyGenerator()
    candidates = gen.generate_candidates(n_candidates)

    # 3. Backtest & Eval
    engine = FoundryEngine()
    wf = WalkForward(n_folds=2 if fast_mode else 4)

    results = []

    for cand in candidates:
        strat = GeneratedStrategy(cand)

        # We need to run WF
        splits = wf.split(df_nifty)

        fold_metrics = []
        passed_folds = 0

        for train, test in splits:
            # We train on Train (optimize? No, we generate random fixed params).
            # We just validate on Test.
            # Actually WF implies training on window to select params, then testing.
            # But our strategies are "Generated with Params".
            # So we just evaluate performance on Test chunks (OOS).

            # Generate positions on full DF to handle indicators warmup?
            # Or just on test?
            # Ideally generate on full, slice positions.

            full_pos = strat.generate_positions(df_nifty)
            test_pos = full_pos.loc[test.index]

            res = engine.run(test, test_pos) # Pass full test DF? Yes.
            met = engine.calculate_metrics(res["trades"])

            # Calculate MaxDD/Sharpe for this fold
            # Need equity curve from engine
            # Engine returns trades.
            # Let's reconstruct or assume calculate_metrics does it?
            # calculate_metrics is basic.
            # Engine.run_vectorized might be better for metrics.

            # Use vectorized for fast metrics
            v_res = engine.run_vectorized(test, test_pos)
            fold_metrics.append(v_res)

            if v_res["sharpe"] > 0 and v_res["total_return"] > 0:
                passed_folds += 1

        # Aggregate OOS metrics
        # Average Sharpe, Total Return
        if not fold_metrics:
            continue

        avg_sharpe = sum(m["sharpe"] for m in fold_metrics) / len(fold_metrics)
        avg_cagr = sum(m["cagr"] for m in fold_metrics) / len(fold_metrics)
        avg_dd = min(m["max_dd"] for m in fold_metrics) # Worst case DD
        avg_turnover = sum(m["turnover"] for m in fold_metrics) / len(fold_metrics)

        cand_res = {
            **cand,
            "sharpe": avg_sharpe,
            "cagr": avg_cagr,
            "max_dd": avg_dd,
            "turnover": avg_turnover,
            "passed_folds": passed_folds,
            "trades": sum(m["trades"] for m in fold_metrics)
        }

        # Sanity
        passed, reason = check_sanity(cand_res, fast_mode)
        if passed:
            results.append(cand_res)
        else:
            logger.debug("Candidate rejected", id=cand["id"], reason=reason)

    # 4. Rank
    ranker = Ranker()
    ranked_df = ranker.rank_candidates(results)

    if not ranked_df.empty:
        # Save results
        ranked_df.to_csv(f"{run_dir}/candidates.csv")

        best = ranked_df.iloc[0].to_dict()
        current = load_champion()

        if fast_mode:
            logger.info("Fast mode: skipping promotion")
        else:
            if should_promote(best, current):
                save_champion(best, "Score improvement")

        # Leaderboard Update (Append)
        # TODO: Implement global leaderboard file update
        pass

    # 5. Live Signal
    publish_signal("NIFTY")

    logger.info("Run completed")

if __name__ == "__main__":
    main()
