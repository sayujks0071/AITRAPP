"""
Hourly Runner for StrategyFoundry.
"""
import os
import sys
import json
import logging
import argparse
from datetime import datetime
from pathlib import Path
import pandas as pd

from packages.strategy_foundry.data.loader import load_instrument_data
from packages.strategy_foundry.factory.generator import StrategyGenerator
from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.selection.ranker import WalkForwardEvaluator, Ranker
from packages.strategy_foundry.live.signal_publisher import SignalPublisher
from packages.strategy_foundry.factory.grammar import StrategyCandidate

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("StrategyFoundry")

BASE_DIR = Path(__file__).parent
RESULTS_DIR = BASE_DIR / "results"
RUNS_DIR = RESULTS_DIR / "runs"
CHAMPIONS_DIR = RESULTS_DIR / "champions"

INSTRUMENTS = ["NIFTY", "SENSEX"]

def ensure_dirs():
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    CHAMPIONS_DIR.mkdir(parents=True, exist_ok=True)

def save_champion(candidate, score, filepath):
    data = candidate.to_json()
    with open(filepath, "w") as f:
        f.write(data)

def load_champion(filepath):
    if not filepath.exists():
        return None
    with open(filepath, "r") as f:
        return StrategyCandidate.from_json(f.read())

def main():
    ensure_dirs()

    # Determine Mode
    fast_mode = os.environ.get("FAST_MODE", "0") == "1"

    # Config
    n_candidates = 10 if fast_mode else 50
    n_folds = 2 if fast_mode else 3

    run_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    current_run_dir = RUNS_DIR / run_ts
    current_run_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Starting run {run_ts} (FAST_MODE={fast_mode})")

    # Initialize Generator
    generator = StrategyGenerator()

    leaderboard = []

    # Process Instruments for Strategy Generation
    for instrument in INSTRUMENTS:
        logger.info(f"Processing {instrument}...")

        # 1. Load Data
        try:
            df = load_instrument_data(instrument)
        except Exception as e:
            logger.error(f"Failed to load data for {instrument}: {e}")
            continue

        # 2. Generate Candidates
        candidates = generator.generate(n_candidates)
        logger.info(f"Generated {len(candidates)} candidates")

        # 3. Backtest & Evaluate
        engine = BacktestEngine(df)
        evaluator = WalkForwardEvaluator(df, n_folds=n_folds)

        best_score = -999
        best_candidate = None
        best_metrics = None

        for cand in candidates:
            wf_res = evaluator.evaluate(cand, engine)

            if wf_res.get("status") == "skipped":
                continue

            score = Ranker.score(wf_res)

            # Sanity filters
            if wf_res["max_dd"] > 0.35: continue
            if wf_res["positive_folds"] < (1 if fast_mode else 2): continue

            leaderboard.append({
                "instrument": instrument,
                "id": cand.id,
                "score": score,
                "sharpe": wf_res["avg_sharpe"],
                "cagr": wf_res["avg_cagr"],
                "max_dd": wf_res["max_dd"]
            })

            if score > best_score:
                best_score = score
                best_candidate = cand
                best_metrics = wf_res

        # 4. Promotion Logic
        if best_candidate:
            logger.info(f"Best candidate for {instrument}: {best_candidate.id} Score: {best_score:.4f}")

            current_champ_file = CHAMPIONS_DIR / f"current_{instrument}.json"

            promote = False
            # Simple threshold promotion if no existing champion
            if not current_champ_file.exists():
                if best_score > 0.2:
                    promote = True
            else:
                # In a real system, we'd compare against current champion's score on NEW data
                # For now, we assume if score is very high we promote
                if best_score > 0.5:
                     promote = True

            if promote:
                logger.info(f"Promoting new champion for {instrument}")
                save_champion(best_candidate, best_score, current_champ_file)
                # Archive
                save_champion(best_candidate, best_score, CHAMPIONS_DIR / f"{run_ts}_{instrument}_{best_candidate.id}.json")

    # Save Leaderboard
    lb_df = pd.DataFrame(leaderboard)
    if not lb_df.empty:
        lb_df.sort_values("score", ascending=False, inplace=True)
        lb_df.to_csv(RESULTS_DIR / "leaderboard.csv", index=False)
        with open(RESULTS_DIR / "leaderboard.md", "w") as f:
            f.write(lb_df.head(20).to_markdown())

    # 5. Live Signal Generation (using persisted champions)
    publisher = SignalPublisher(RESULTS_DIR)

    for instrument in INSTRUMENTS:
         champ_file = CHAMPIONS_DIR / f"current_{instrument}.json"
         if champ_file.exists():
             try:
                 champ = load_champion(champ_file)
                 df = load_instrument_data(instrument)
                 engine = BacktestEngine(df)

                 # Run on FULL data to get current position
                 res = engine.run(champ)
                 current_pos = res.get("current_position", 0)
                 metrics = res.get("metrics", {})

                 logger.info(f"Champion {champ.id} for {instrument}: Position={current_pos}")

                 publisher.publish(champ, current_pos, instrument, metrics)

             except Exception as e:
                 logger.error(f"Failed to publish signal for {instrument}: {e}")

    logger.info("Run complete.")

if __name__ == "__main__":
    main()
