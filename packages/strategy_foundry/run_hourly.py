"""
Strategy Foundry Hourly Runner
"""
import os
import sys
import yaml
import json
import structlog
import pandas as pd
from datetime import datetime
import pytz

# Ensure packages path is in sys.path
sys.path.append(os.getcwd())

from packages.strategy_foundry.data.loader import DataLoader
from packages.strategy_foundry.factory.grammar import StrategyGrammar
from packages.strategy_foundry.backtest.walkforward import WalkForwardValidator
from packages.strategy_foundry.backtest.sanity import SanityCheck
from packages.strategy_foundry.selection.ranker import Ranker, ChampionStore
from packages.strategy_foundry.live.signal_publisher import SignalPublisher

logger = structlog.get_logger(__name__)
IST = pytz.timezone("Asia/Kolkata")

class FoundryRunner:
    def __init__(self):
        self.config_path = "packages/strategy_foundry/configs/foundry.yaml"
        with open(self.config_path) as f:
            self.config = yaml.safe_load(f)

        self.fast_mode = os.environ.get("FAST_MODE", "0") == "1"
        self.loader = DataLoader()
        self.ranker = Ranker()
        self.store = ChampionStore()

        ts = datetime.now(IST).strftime("%Y%m%d_%H%M%S")
        self.run_dir = os.path.join(self.config['system']['results_dir'], "runs", ts)
        os.makedirs(self.run_dir, exist_ok=True)

    def run(self):
        logger.info("Starting Foundry Run", fast_mode=self.fast_mode)

        instruments = ["NIFTY"] # For now focus on NIFTY as per spec examples
        timeframes = self.config['data']['intraday']['timeframes']

        all_results = []

        # 1. Data Loading
        data_cache = {}
        for inst in instruments:
            for tf in timeframes:
                # In fast mode, fetch fewer days? handled in loader call
                days = 30 if self.fast_mode else None
                df = self.loader.get_data(inst, tf, days=days)
                data_cache[(inst, tf)] = df

            # Load Daily for Sanity
            daily_df = self.loader.get_data(inst, "1D", days=365)
            data_cache[(inst, "1D")] = daily_df

        # 2. Generation & Backtest
        n_candidates = self.config['generation']['fast_mode_candidates'] if self.fast_mode else self.config['generation']['full_mode_candidates']

        candidates = []
        for _ in range(n_candidates):
            candidates.append(StrategyGrammar.random_strategy())

        # Save candidates
        with open(os.path.join(self.run_dir, "candidates.json"), "w") as f:
            json.dump(candidates, f, indent=2)

        logger.info(f"Generated {len(candidates)} candidates")

        folds = self.config['backtest']['folds']['fast_mode'] if self.fast_mode else self.config['backtest']['folds']['default']

        for cand in candidates:
            for inst in instruments:
                # We will rank per timeframe
                # Intraday Check
                for tf in timeframes:
                    df = data_cache[(inst, tf)]
                    if df.empty: continue

                    if len(df) < 100: continue # Skip if not enough data

                    # Walk Forward Evaluation
                    validator = WalkForwardValidator(df, cand, self.config['backtest']['costs'], folds=folds)
                    metrics = validator.run()

                    if not metrics: continue

                    metrics["instrument"] = inst
                    metrics["timeframe"] = tf
                    metrics["candidate_id"] = cand["id"]

                    all_results.append({
                        "id": cand["id"],
                        "strategy": cand,
                        "instrument": inst,
                        "timeframe": tf,
                        "metrics": metrics,
                        "score": 0 # to be calculated
                    })

        # 3. Ranking
        ranked_df = self.ranker.rank(all_results)

        # Save Metrics
        if not ranked_df.empty:
            ranked_df.drop(columns=["strategy"], errors='ignore').to_csv(os.path.join(self.run_dir, "metrics.csv"), index=False)

            # Generate Leaderboards per TF
            for tf in timeframes:
                tf_df = ranked_df[ranked_df["timeframe"] == tf]
                if not tf_df.empty:
                    md_path = os.path.join(self.run_dir, f"leaderboard_{tf}.md")
                    tf_df.head(10).to_markdown(md_path)

        # 4. Selection & Promotion (Only in Full Mode)
        champion = None
        if not self.fast_mode and not ranked_df.empty:
            # Pick best across all? Or best per instrument?
            # Let's pick global best for NIFTY
            nifty_df = ranked_df[ranked_df["instrument"] == "NIFTY"]
            if not nifty_df.empty:
                # Prefer 15m? Spec says blended.
                # Simplified: Pick top score irrespective of TF for now, then apply sanity.
                best_row = nifty_df.iloc[0]

                # Sanity Check (1D)
                daily_df = data_cache[("NIFTY", "1D")]
                cand_obj = [c for c in candidates if c["id"] == best_row["id"]][0]

                sanity_checker = SanityCheck(daily_df, self.config['backtest']['costs'])
                passed_sanity = sanity_checker.check(cand_obj)

                if passed_sanity:
                    # Check Promotion
                    current = self.store.get_current_champion()

                    # Construct candidate dict
                    candidate_record = {
                        "id": best_row["id"],
                        "strategy": cand_obj,
                        "metrics": best_row["metrics"],
                        "score": best_row["score"],
                        "timeframe": best_row["timeframe"],
                        "timestamp": datetime.now(IST).isoformat()
                    }

                    if self.ranker.evaluate_promotion(candidate_record.copy(), current, self.config): # copy to avoid modification issues
                         self.store.promote_new_champion(candidate_record, ts)
                         champion = candidate_record
                    else:
                        champion = current # Keep current
                else:
                    logger.warning(f"Candidate {cand_obj['id']} failed 1D sanity")

        # 5. Live Signal (If eligible)
        current_champ = self.store.get_current_champion()
        if current_champ:
            publisher = SignalPublisher(self.config_path)
            publisher.publish(current_champ, "NIFTY")

        logger.info("Foundry Run Completed")

if __name__ == "__main__":
    runner = FoundryRunner()
    runner.run()
