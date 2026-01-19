"""
Hourly Runner for Strategy Foundry.
"""
import os
import sys
import json
import logging
import pandas as pd
from datetime import datetime
from pathlib import Path
import structlog

# Setup logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    logger_factory=structlog.PrintLoggerFactory(),
)
logger = structlog.get_logger()

from packages.strategy_foundry.data.loader import DataLoader
from packages.strategy_foundry.factory.generator import StrategyGenerator
from packages.strategy_foundry.factory.registry import CandidateRegistry
from packages.strategy_foundry.backtest.walkforward import WalkForwardAnalyst
from packages.strategy_foundry.backtest.sanity import SanityChecker
from packages.strategy_foundry.selection.ranker import Ranker
from packages.strategy_foundry.selection.champion_store import ChampionStore
from packages.strategy_foundry.selection.promote import should_promote, is_live_eligible
from packages.strategy_foundry.live.signal_publisher import SignalPublisher

def main():
    # 1. Config
    fast_mode = os.getenv("FAST_MODE", "0") == "1"

    # Pr run detection (CI usually sets CI=true)
    if os.getenv("CI") == "true" and os.getenv("GITHUB_EVENT_NAME") == "pull_request":
        fast_mode = True

    n_candidates = 10 if fast_mode else 50
    folds = 2 if fast_mode else 3

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = Path(f"packages/strategy_foundry/results/runs/{timestamp}")
    run_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Starting Strategy Foundry Run", mode="FAST" if fast_mode else "FULL", timestamp=timestamp)

    # 2. Load Data
    loader = DataLoader()
    try:
        # Update cache if needed
        # In CI, we might want to force download if cache empty.
        df_nifty = loader.get_nifty()
        # df_sensex = loader.get_sensex() # Optional
    except Exception as e:
        logger.error("Failed to load data", error=str(e))
        sys.exit(1)

    # 3. Generate Candidates
    generator = StrategyGenerator()
    registry = CandidateRegistry()

    logger.info(f"Generating {n_candidates} candidates...")

    unique_count = 0
    attempts = 0
    while unique_count < n_candidates and attempts < n_candidates * 5:
        strat = generator.generate_candidate()
        if registry.add(strat):
            unique_count += 1
        attempts += 1

    # 4. Backtest & Evaluate
    wfa = WalkForwardAnalyst(folds=folds)
    results = []

    candidates = list(registry.candidates.values())
    for i, strat in enumerate(candidates):
        res = wfa.evaluate(strat, df_nifty)

        if not res["valid"]:
            continue

        # Sanity Checks
        full_metrics = res.get("full_metrics", {})
        trades_df = res.get("full_trades", pd.DataFrame())

        # Check min trades (sanity)
        min_trades = 1 if fast_mode else 30
        if not SanityChecker.check_min_trades(trades_df, min_trades):
            logger.info("Rejected: min_trades", got=len(trades_df), needed=min_trades, id=strat.id)
            continue

        max_dd_limit = 1000.0 if fast_mode else 35.0
        if not SanityChecker.check_max_drawdown(full_metrics, max_dd_pct=max_dd_limit):
            logger.info("Rejected: max_dd", got=full_metrics.get("max_drawdown"), id=strat.id)
            continue

        if not SanityChecker.check_oos_consistency(res["folds"]):
            if not fast_mode: # Strict check in full mode
                 continue

        results.append({
            "strategy_id": strat.id,
            "strategy": strat,
            "metrics": res
        })

        if (i+1) % 10 == 0:
            logger.info(f"Processed {i+1}/{len(candidates)}")

    logger.info(f"Qualified candidates: {len(results)}")

    # 5. Rank
    leaderboard = Ranker.rank_candidates(results)

    if leaderboard.empty:
        logger.warning("No candidates qualified.")
        sys.exit(0)

    # Save Run Candidates
    candidates_data = []
    for res in results:
        candidates_data.append({
            "id": res["strategy_id"],
            "description": res["strategy"].describe(),
            "metrics": {k: float(v) if isinstance(v, (int, float)) else str(v) for k, v in res["metrics"].items() if k not in ["full_equity", "full_trades", "folds"]}
        })

    with open(run_dir / "candidates.json", "w") as f:
        json.dump(candidates_data, f, indent=2)

    # Save Leaderboard
    leaderboard.to_csv(run_dir / "leaderboard.csv", index=False)
    leaderboard.to_csv("packages/strategy_foundry/results/leaderboard.csv", index=False) # Latest

    # Generate Leaderboard MD
    md_content = "# Strategy Foundry Leaderboard\n\n"
    md_content += f"Run: {timestamp} (Mode: {'FAST' if fast_mode else 'FULL'})\n\n"
    md_content += leaderboard.head(20).to_markdown(index=False)
    with open("packages/strategy_foundry/results/leaderboard.md", "w") as f:
        f.write(md_content)

    # 6. Champion Selection
    champ_store = ChampionStore()
    current_champ = champ_store.load_current_champion()

    top_candidate_row = leaderboard.iloc[0]
    top_candidate_res = next(r for r in results if r["strategy_id"] == top_candidate_row["id"])

    top_candidate_blob = {
        "score": top_candidate_row["score"],
        "metrics": top_candidate_res["metrics"]
    }

    if should_promote(top_candidate_blob, current_champ):
        logger.info("New Champion Promoted!", id=top_candidate_row["id"], score=top_candidate_row["score"])

        strat_serial = champ_store.serialize_strategy(top_candidate_res["strategy"])

        # Strip heavy data from metrics for storage
        metrics_lite = top_candidate_res["metrics"].copy()
        metrics_lite.pop("full_equity", None)
        metrics_lite.pop("full_trades", None)
        metrics_lite.pop("folds", None) # Store fold summary?

        champ_store.save_champion(
            strategy_data=strat_serial,
            metrics=metrics_lite,
            score=top_candidate_row["score"],
            timestamp=timestamp
        )
    else:
        logger.info("Current champion retained.")

    # 7. Publish Live Signal
    publisher = SignalPublisher()
    publisher.publish()

    logger.info("Run Complete.")

if __name__ == "__main__":
    main()
