import os
import sys
import logging
import pandas as pd
from datetime import datetime
import pytz
import yaml

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from packages.strategy_foundry.data.loader import DataLoader
from packages.strategy_foundry.factory.generator import StrategyGenerator
from packages.strategy_foundry.factory.registry import CandidateRegistry
from packages.strategy_foundry.backtest.walkforward import WalkForwardEvaluator
from packages.strategy_foundry.backtest.sanity import SanityChecker
from packages.strategy_foundry.selection.ranker import Ranker
from packages.strategy_foundry.selection.promote import Promoter
from packages.strategy_foundry.live.signal_publisher import SignalPublisher

def load_config():
    path = "packages/strategy_foundry/configs/foundry.yaml"
    if os.path.exists(path):
        with open(path, 'r') as f:
            return yaml.safe_load(f)
    return {}

def run():
    # 1. Config & Setup
    config_yaml = load_config()
    foundry_conf = config_yaml.get('foundry', {})

    FAST_MODE = os.environ.get('FAST_MODE', '0') == '1'
    N_CANDIDATES = foundry_conf.get('fast_mode_candidates', 15) if FAST_MODE else foundry_conf.get('max_candidates', 80)
    FOLDS = foundry_conf.get('fast_mode_folds', 2) if FAST_MODE else foundry_conf.get('folds', 4)

    logger.info(f"Starting Strategy Foundry (FAST_MODE={FAST_MODE}, N={N_CANDIDATES}, FOLDS={FOLDS})")

    instruments = ['NIFTY', 'SENSEX']
    run_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = f"packages/strategy_foundry/results/runs/{run_ts}"
    os.makedirs(run_dir, exist_ok=True)

    loader = DataLoader()
    generator = StrategyGenerator()

    # Generate Candidates
    candidates = []
    seen_ids = set()
    while len(candidates) < N_CANDIDATES:
        cand = generator.generate_candidate()
        if cand.strategy_id not in seen_ids:
            candidates.append(cand)
            seen_ids.add(cand.strategy_id)

    # Save candidates
    CandidateRegistry.save_candidates(candidates, f"{run_dir}/candidates.json")

    leaderboard_rows = []

    for instrument in instruments:
        logger.info(f"Processing {instrument}")

        # 2. Data
        try:
            df_5m = loader.get_data(instrument, "5m")
            df_15m = loader.get_data(instrument, "15m")
            df_1d = loader.get_data(instrument, "1d")

            if df_5m is None or df_5m.empty or df_15m is None or df_15m.empty:
                logger.error(f"Missing intraday data for {instrument}. Skipping.")
                continue
        except Exception as e:
            logger.error(f"Failed to load data for {instrument}: {e}")
            continue

        # 3. Evaluate (Walk Forward)
        wf_5m = WalkForwardEvaluator(df_5m, folds=FOLDS)
        wf_15m = WalkForwardEvaluator(df_15m, folds=FOLDS)

        results_5m = []
        results_15m = []

        for cand in candidates:
            # 5m
            try:
                m5 = wf_5m.evaluate(cand)
                results_5m.append({"strategy": cand, "metrics": m5})
            except Exception as e:
                logger.warning(f"Failed 5m eval for {cand.strategy_id}: {e}")

            # 15m
            try:
                m15 = wf_15m.evaluate(cand)
                results_15m.append({"strategy": cand, "metrics": m15})
            except Exception as e:
                logger.warning(f"Failed 15m eval for {cand.strategy_id}: {e}")

        # 4. Rank & Blend
        rank_5m = Ranker.rank(results_5m)
        rank_15m = Ranker.rank(results_15m)

        # Save raw rankings
        if not rank_5m.empty:
            rank_5m.to_csv(f"{run_dir}/{instrument}_ranking_5m.csv", index=False)
        if not rank_15m.empty:
            rank_15m.to_csv(f"{run_dir}/{instrument}_ranking_15m.csv", index=False)

        # Merge for Blended Score
        # We assume same strategy_id in both
        if not rank_5m.empty and not rank_15m.empty:
            merged = pd.merge(rank_5m[['strategy_id', 'score', 'sharpe', 'max_dd', 'sharpe_std', 'positive_folds']],
                              rank_15m[['strategy_id', 'score', 'sharpe', 'max_dd', 'sharpe_std', 'positive_folds']],
                              on='strategy_id', suffixes=('_5m', '_15m'))

            merged['blended_score'] = 0.6 * merged['score_15m'] + 0.4 * merged['score_5m']
            merged['avg_sharpe'] = 0.6 * merged['sharpe_15m'] + 0.4 * merged['sharpe_5m']
            merged['avg_max_dd'] = merged[['max_dd_15m', 'max_dd_5m']].max(axis=1)

            # Sort by blended
            merged.sort_values('blended_score', ascending=False, inplace=True)
            merged.to_csv(f"{run_dir}/{instrument}_ranking_blended.csv", index=False)

            # Find the full candidate object for top
            cand_map = {c.strategy_id: c for c in candidates}

            # 5. Sanity Check (Top 10)
            top_candidates = merged.head(10)
            sanity_checker = SanityChecker(df_1d, wf_5m.cost_model)

            champion_candidate = None
            champion_row = None

            for _, row in top_candidates.iterrows():
                sid = row['strategy_id']
                cand = cand_map.get(sid)
                if not cand: continue

                # Run Sanity
                sanity_res = sanity_checker.check(cand)
                if sanity_res['passed']:
                    # Found our potential champion
                    champion_candidate = cand
                    champion_row = row.to_dict()
                    champion_row['score'] = row['blended_score']
                    champion_row['sharpe'] = row['avg_sharpe'] # Important for promotion check
                    champion_row['max_dd'] = row['avg_max_dd']
                    champion_row['strategy_config'] = cand.to_dict()
                    logger.info(f"Champion found for {instrument}: {sid} (Score: {row['blended_score']:.2f})")
                    break
                else:
                    logger.info(f"Strategy {sid} failed sanity: {sanity_res['reason']}")

            # 6. Promote (Only in Full Mode usually? Prompt says DO NOT promote in FAST_MODE)
            if champion_candidate:
                if not FAST_MODE:
                    promoter = Promoter(instrument, "blended")
                    promoted = promoter.check_and_promote(champion_row)
                else:
                    promoted = False
                    logger.info("FAST_MODE: Skipping promotion.")

                leaderboard_rows.append({
                    "instrument": instrument,
                    "top_strategy": champion_candidate.strategy_id,
                    "score": champion_row['score'],
                    "sharpe": champion_row['sharpe'],
                    "promoted": promoted
                })

                # 7. Publish Signal
                # Only if we found a champion (regardless of new promotion, we might use existing)
                # But here we publish based on the *just selected* champion?
                # SignalPublisher loads from disk ("current.json").
                # If we promoted, it's on disk.
                # If we didn't promote, "current.json" is old champion.
                # Should we publish signal for the NEW winner even if not improved enough to replace old?
                # No, "Champion" implies the one on the throne.
                # So SignalPublisher uses whatever is on disk.

                # Check Signal for this instrument
                publisher = SignalPublisher(instrument, "blended")
                publisher.publish()
            else:
                 logger.warning(f"No valid champion found for {instrument} after sanity checks.")

    # 8. Update Leaderboard MD
    if leaderboard_rows:
        lb_df = pd.DataFrame(leaderboard_rows)
        lb_path = "packages/strategy_foundry/results/leaderboard.md"
        # Append or Create
        mode = 'a' if os.path.exists(lb_path) else 'w'
        with open(lb_path, mode) as f:
            f.write(f"\n## Run {run_ts}\n")
            f.write(lb_df.to_markdown(index=False))
            f.write("\n")

    logger.info("Run completed")

if __name__ == "__main__":
    run()
