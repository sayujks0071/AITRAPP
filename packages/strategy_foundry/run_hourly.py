import os
import sys
import logging
from datetime import datetime
import pandas as pd
import pytz

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from packages.strategy_foundry.data.loader import DataLoader
from packages.strategy_foundry.factory.generator import StrategyGenerator
from packages.strategy_foundry.backtest.walkforward import WalkForwardEvaluator
from packages.strategy_foundry.selection.ranker import Ranker
from packages.strategy_foundry.selection.promote import Promoter
from packages.strategy_foundry.live.signal_publisher import SignalPublisher
from packages.strategy_foundry.factory.registry import CandidateRegistry

def run():
    # 1. Config
    FAST_MODE = os.environ.get('FAST_MODE', '0') == '1'
    N_CANDIDATES = 10 if FAST_MODE else 50
    FOLDS = 2 if FAST_MODE else 3

    logger.info(f"Starting Strategy Foundry (FAST_MODE={FAST_MODE})")

    instruments = ['NIFTY', 'SENSEX']

    # Timestamp for artifacts
    run_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = f"packages/strategy_foundry/results/runs/{run_ts}"
    os.makedirs(run_dir, exist_ok=True)

    leaderboard_rows = []

    loader = DataLoader()
    generator = StrategyGenerator()
    promoter = Promoter() # Defaults to NIFTY, we might need one per instrument?
    # Promoter uses ChampionStore which handles file per instrument.
    # But Promoter init takes instrument.

    for instrument in instruments:
        logger.info(f"Processing {instrument}")

        # 2. Data
        try:
            df = loader.get_data(instrument)
            if df is None or df.empty:
                logger.error(f"No data for {instrument}")
                continue
        except Exception as e:
            logger.error(f"Failed to load data for {instrument}: {e}")
            continue

        # 3. Generate Candidates
        candidates = []
        # Attempt to load previous candidates to mutate?
        # Requirement says "Generate N candidates per run". "Self-generating".
        # We can start fresh or keep some.
        # For now, generate fresh N.

        seen_ids = set()
        while len(candidates) < N_CANDIDATES:
            cand = generator.generate_candidate()
            if cand.strategy_id not in seen_ids:
                candidates.append(cand)
                seen_ids.add(cand.strategy_id)

        # Save candidates
        CandidateRegistry.save_candidates(candidates, f"{run_dir}/{instrument}_candidates.json")

        # 4. Evaluate (Walk Forward)
        wf = WalkForwardEvaluator(df, folds=FOLDS)
        results = []

        for cand in candidates:
            try:
                # We need to map instrument type. NIFTY/SENSEX are Indices (EQUITY/FUTURE logic?)
                # We trade NIFTY Futures usually or ETFs.
                # CostsAdapter defaults to Equity structure but we can pass FUTURE.
                # Let's assume FUTURE for Indices.
                metrics_list = wf.evaluate(cand, instrument_type='FUTURE')

                # Sanity Check?
                # We rely on Ranker/Promoter to filter bad ones.

                results.append({
                    "strategy": cand,
                    "metrics": metrics_list
                })
            except Exception as e:
                logger.warning(f"Failed to evaluate {cand.strategy_id}: {e}")

        # 5. Rank
        ranked_df = Ranker.rank(results)
        ranked_df.to_csv(f"{run_dir}/{instrument}_ranking.csv", index=False)

        # 6. Promote
        if not ranked_df.empty:
            top_row = ranked_df.iloc[0].to_dict()
            promoter_inst = Promoter(instrument)
            promoted = promoter_inst.check_and_promote(top_row)
            if promoted:
                logger.info(f"Promoted new champion for {instrument}: {top_row['strategy_id']}")

            # Add to leaderboard list
            leaderboard_rows.append({
                "instrument": instrument,
                "top_strategy": top_row['strategy_id'],
                "score": top_row['score'],
                "sharpe": top_row['avg_sharpe'],
                "max_dd": top_row['max_dd'],
                "promoted": promoted
            })

        # 7. Publish Live Signal (if eligible)
        # Only for NIFTY/SENSEX (we iterate them)
        # SignalPublisher handles "load current champion".
        publisher = SignalPublisher(instrument)
        publisher.publish()

    # 8. Update Leaderboard MD
    lb_df = pd.DataFrame(leaderboard_rows)
    lb_path = "packages/strategy_foundry/results/leaderboard.md"

    with open(lb_path, 'a') as f:
        f.write(f"\n## Run {run_ts}\n")
        f.write(lb_df.to_markdown(index=False))
        f.write("\n")

    logger.info("Run completed")

if __name__ == "__main__":
    run()
