import os
import sys
import structlog
import pandas as pd
from datetime import datetime
from pathlib import Path

from packages.strategy_foundry.data.loader import DataLoader
from packages.strategy_foundry.factory.generator import StrategyGenerator
from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.backtest.walkforward import get_folds
from packages.strategy_foundry.backtest.sanity import check_sanity, check_daily_sanity
from packages.strategy_foundry.selection.ranker import rank_candidates, calculate_score
from packages.strategy_foundry.selection.champion_store import load_champion, save_champion
from packages.strategy_foundry.selection.promote import should_promote
from packages.strategy_foundry.live.signal_publisher import publish_signal

logger = structlog.get_logger(__name__)

def run():
    # 1. Config
    fast_mode = os.getenv("FAST_MODE", "0") == "1"
    mode = "fast" if fast_mode else "full"

    n_gen = 15 if fast_mode else 80
    n_folds = 2 if fast_mode else 4

    logger.info("Starting Foundry Run", mode=mode, n_gen=n_gen, n_folds=n_folds)

    loader = DataLoader()
    engine = BacktestEngine()
    generator = StrategyGenerator()

    timeframes = ["5m", "15m"]
    results = []

    # 2. Loop Timeframes
    for tf in timeframes:
        logger.info(f"Processing {tf}")
        # Load Data
        df = loader.get_data("NIFTY", tf)
        if df.empty:
            logger.error(f"No data for {tf}")
            continue

        folds = get_folds(df, n_folds)

        # Generate Candidates
        candidates = generator.generate_candidates(n_gen)

        for cand in candidates:
            fold_metrics = []
            passed_folds = 0

            # Walk Forward Validation
            for fold_df in folds:
                res = engine.run(cand, fold_df)
                m = res["metrics"]
                fold_metrics.append(m)
                # Check if this fold is "positive" (profit factor > 1)
                if m["profit_factor"] > 1.0:
                    passed_folds += 1

            # Run on full data for final metrics
            full_res = engine.run(cand, df)
            metrics = full_res["metrics"]

            # Sanity Check
            # Require 3/4 passed folds (or 1/2 in fast)
            threshold = n_folds * 0.75
            if passed_folds >= threshold:
                if check_sanity(metrics, tf, mode):
                    results.append({
                        "strategy_id": cand.strategy_id,
                        "timeframe": tf,
                        "metrics": metrics,
                        "fold_metrics": fold_metrics,
                        "spec": cand.to_dict(),
                        "passed_folds": passed_folds
                    })

    # 3. Rank
    if not results:
        logger.warning("No candidates passed sanity checks")
        publish_signal() # Might publish Skipped
        return

    ranked_df = rank_candidates(results)
    best = ranked_df.iloc[0]

    logger.info("Best Candidate Found", id=best["strategy_id"], score=best["score"])

    # 4. Daily Sanity Overlay
    # Run best on 1D
    df_1d = loader.get_data("NIFTY", "1d")
    spec_obj = generator.generate_random() # Dummy to get class
    # Reconstruct spec object from dict
    from packages.strategy_foundry.factory.grammar import StrategySpec
    best_spec = StrategySpec.from_dict(best["spec"])

    res_1d = engine.run(best_spec, df_1d)
    if not check_daily_sanity(res_1d["metrics"]):
        logger.warning("Best candidate failed daily sanity", id=best["strategy_id"])
        # Logic to reject? For now just log.
        pass

    # 5. Promotion
    current_champ = load_champion()

    should_up, reason = should_promote(best.to_dict(), current_champ)

    if should_up:
        logger.info("Promoting new champion", reason=reason)
        # We need to pass the timeframe of the best candidate
        # best is a Series/dict from results
        save_champion(best.to_dict(), best["metrics"], best["spec"])
    else:
        logger.info("Keeping current champion", reason=reason)

    # 6. Publish Signal
    publish_signal()

    # 7. Generate Artifacts
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    res_dir = Path(f"packages/strategy_foundry/results/runs/{ts}")
    res_dir.mkdir(parents=True, exist_ok=True)

    ranked_df.to_csv(res_dir / "leaderboard.csv", index=False)

    # Markdown summary
    md = f"# Run {ts}\n\nMode: {mode}\n\n"
    md += "## Top 10 Candidates\n\n"
    md += ranked_df.head(10).to_markdown() if not ranked_df.empty else "No results"

    with open(res_dir / "summary.md", "w") as f:
        f.write(md)

    logger.info("Run Complete", artifacts=str(res_dir))

if __name__ == "__main__":
    run()
