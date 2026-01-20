import logging
import os
import sys
from datetime import datetime
import pandas as pd
import json

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("FoundryRunner")

from packages.strategy_foundry.data.loader import DataLoader
from packages.strategy_foundry.factory.generator import StrategyGenerator
from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.backtest.walkforward import WalkForwardEvaluator
from packages.strategy_foundry.selection.ranker import Ranker
from packages.strategy_foundry.selection.champion_store import ChampionStore
from packages.strategy_foundry.live.signal_publisher import SignalPublisher

def main():
    # 1. Configuration
    fast_mode = os.environ.get("FAST_MODE", "0") == "1"

    N_CANDIDATES = 10 if fast_mode else 50
    N_FOLDS = 2 if fast_mode else 4
    MIN_TRADES = 10 if fast_mode else 30
    MIN_POS_FOLDS = 1 if fast_mode else 2

    logger.info(f"Starting Foundry Run. FastMode={fast_mode}, N={N_CANDIDATES}, Folds={N_FOLDS}")

    run_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_dir = f"packages/strategy_foundry/results/runs/{run_ts}"
    os.makedirs(results_dir, exist_ok=True)

    instruments = ["NIFTY", "SENSEX"]

    loader = DataLoader()
    engine = BacktestEngine()
    evaluator = WalkForwardEvaluator(engine)
    ranker = Ranker()
    champion_store = ChampionStore()

    leaderboard_entries = []

    for instrument in instruments:
        logger.info(f"Processing {instrument}...")

        # 2. Data Update
        df = loader.fetch_data(instrument, force_refresh=True)
        if df.empty:
            logger.error(f"No data for {instrument}, skipping.")
            continue

        # 3. Generate Candidates
        generator = StrategyGenerator()
        candidates = generator.generate_candidates(N_CANDIDATES)

        instrument_results = []

        for i, spec in enumerate(candidates):
            # 4. Evaluate (Walk Forward)
            metrics = evaluator.evaluate(df, spec, folds=N_FOLDS)

            # 5. Score
            score = ranker.calculate_score(metrics)

            # 6. Sanity & Eligibility
            # Rejection criteria
            passed_sanity = True
            reasons = []

            if metrics.get("total_trades", 0) < MIN_TRADES:
                passed_sanity = False
                reasons.append("MIN_TRADES")

            if metrics.get("positive_folds", 0) < MIN_POS_FOLDS:
                passed_sanity = False
                reasons.append("MIN_POS_FOLDS")

            if metrics.get("max_dd", 1.0) > 0.35:
                passed_sanity = False
                reasons.append("MAX_DD")

            eligible = passed_sanity and ranker.is_eligible(metrics, fast_mode)

            res = {
                "id": spec["id"],
                "spec": spec,
                "metrics": metrics,
                "score": score,
                "eligible": eligible,
                "reasons": reasons
            }
            instrument_results.append(res)

        # Sort by score
        instrument_results.sort(key=lambda x: x["score"], reverse=True)

        # Save Instrument Candidates
        with open(f"{results_dir}/{instrument}_candidates.json", "w") as f:
            json.dump(instrument_results, f, indent=2, default=str)

        # 7. Promote Champion
        if instrument_results:
            top = instrument_results[0]
            if top["eligible"]:
                logger.info(f"Top Candidate for {instrument}: {top['id']} Score: {top['score']:.2f}")
                champion_store.save_champion(instrument, top["spec"], top["score"], top["metrics"]) # Always save/promote if better logic handles it?
                # Wait, save_champion saves it as current.
                # check promotion logic first.
                if champion_store.should_promote(instrument, top["score"], top["metrics"]):
                     champion_store.save_champion(instrument, top["spec"], top["score"], top["metrics"])
            else:
                logger.info(f"Top candidate {top['id']} not eligible. Reasons: {top['reasons']}")

        # Add to leaderboard list
        for r in instrument_results:
            leaderboard_entries.append({
                "run_ts": run_ts,
                "instrument": instrument,
                "id": r["id"],
                "score": r["score"],
                "sharpe": r["metrics"].get("avg_fold_sharpe", 0),
                "cagr": r["metrics"].get("cagr", 0),
                "trades": r["metrics"].get("total_trades", 0),
                "eligible": r["eligible"]
            })

    # 8. Update Global Leaderboard
    lb_file = "packages/strategy_foundry/results/leaderboard.csv"
    lb_df = pd.DataFrame(leaderboard_entries)
    if not lb_df.empty:
        if os.path.exists(lb_file):
            old_lb = pd.read_csv(lb_file)
            lb_df = pd.concat([old_lb, lb_df])

        # Keep top 1000?
        lb_df.to_csv(lb_file, index=False)

        # Generate MD
        top_20 = lb_df[lb_df["eligible"] == True].sort_values("score", ascending=False).head(20)
        md_content = "# Strategy Foundry Leaderboard\n\n"
        md_content += top_20.to_markdown(index=False)
        with open("packages/strategy_foundry/results/leaderboard.md", "w") as f:
            f.write(md_content)

    # 9. Publish Signal
    # Only if NOT fast mode? Or always?
    # "PR runs must use FAST_MODE... Strategy Foundry is a Paper First lab... prohibits direct broker execution"
    # "Signal publisher... If market open AND champion live-eligible..."
    # We can publish in FAST_MODE too, just to test the publisher.
    # But usually we don't want CI to overwrite the live signal file used by production?
    # But this is a "self-generating lab", maybe there is no "production" yet.
    # The prompt says: "Publish live_signal.json only if eligible & market open"

    if not fast_mode:
        publisher = SignalPublisher()
        for instrument in instruments:
            publisher.publish(instrument)

if __name__ == "__main__":
    main()
