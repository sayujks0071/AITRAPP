import logging
import os
import json
from datetime import datetime

import pandas as pd
import yaml

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("FoundryRunner")

from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.backtest.walkforward import WalkForwardEvaluator
from packages.strategy_foundry.data.loader import DataLoader
from packages.strategy_foundry.factory.generator import StrategyGenerator
from packages.strategy_foundry.factory.registry import CandidateRegistry
from packages.strategy_foundry.live.signal_publisher import SignalPublisher
from packages.strategy_foundry.selection.champion_store import ChampionStore
from packages.strategy_foundry.selection.ranker import Ranker


def load_config():
    config_path = "packages/strategy_foundry/configs/foundry.yaml"
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            return yaml.safe_load(f)
    return {}

def main():
    # 1. Config
    config = load_config()
    foundry_cfg = config.get("foundry", {})
    selection_cfg = config.get("selection", {})

    fast_mode = os.environ.get("FAST_MODE", "0") == "1"

    n_candidates = foundry_cfg.get("fast_mode_candidates", 10) if fast_mode else foundry_cfg.get("max_candidates", 50)
    n_folds = foundry_cfg.get("fast_mode_folds", 2) if fast_mode else foundry_cfg.get("folds", 4)

    logger.info(f"Starting Foundry Run. FastMode={fast_mode}, N={n_candidates}, Folds={n_folds}")

    run_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_dir = f"packages/strategy_foundry/results/runs/{run_ts}"
    os.makedirs(results_dir, exist_ok=True)

    # Instruments to Research
    instruments = ["NIFTY", "SENSEX"]

    loader = DataLoader()
        exec_cfg = config.get("execution", {})
    slip = exec_cfg.get("slippage_bps_per_side", 5.0)
    # Cost = Tax + Brokerage Proxy
    cost = exec_cfg.get("tax_bps", 3.0) + 0.5
    engine = BacktestEngine(cost_bps=cost, slippage_bps=slip)
    evaluator = WalkForwardEvaluator(engine)
    ranker = Ranker()
    store = ChampionStore()

    all_results = []

    for instrument in instruments:
        logger.info(f"Processing Instrument: {instrument}")

        # 2. Data
        logger.info("Fetching data...")
        df_1d = loader.fetch_data(instrument, "1d", force_refresh=True)

        if df_1d.empty:
            logger.error(f"Failed to fetch 1D data for {instrument}. Skipping.")
            continue

        # 3. Generate
        # We use a distinct set of candidates for each instrument to ensure diversity and fit
        generator = StrategyGenerator()
        candidates = generator.generate_candidates(n_candidates)
        logger.info(f"Generated {len(candidates)} candidates for {instrument}.")

        # Save candidates
        # We append instrument to filename or just save list?
        # Let's save as candidates_{instrument}.json
        # CandidateRegistry assumes one file. Let's subclass or just dump manually here.
        with open(f"{results_dir}/candidates_{instrument}.json", "w") as f:
            json.dump(candidates, f, indent=2)

        # 4. Evaluate
        min_trades = selection_cfg.get("min_trades", 30)
        if fast_mode: min_trades = 10

        instrument_results = []
        for i, spec in enumerate(candidates):
            if i % 10 == 0: logger.info(f"Processing {instrument} {i}/{len(candidates)}")

            metrics = evaluator.evaluate(df_1d, spec, folds=n_folds)

            if not metrics:
                continue

            sanity = metrics.get("sanity", {"late_day_dependence": True, "min_trades": False, "overtrade": True})
            sanity["min_trades"] = metrics.get("total_trades", 0) >= min_trades

            score = ranker.score_candidate(metrics, sanity)
            is_eligible = ranker.is_eligible(metrics, sanity)

            if fast_mode:
                is_eligible = False

            res_entry = {
                "instrument": instrument,
                "spec": spec,
                "metrics": metrics,
                "score": score,
                "eligible": is_eligible
            }
            instrument_results.append(res_entry)
            all_results.append(res_entry)

        # 5. Rank & Promote per Instrument
        instrument_results.sort(key=lambda x: x["score"], reverse=True)

        if instrument_results:
            top_candidate = instrument_results[0]
            logger.info(f"Top {instrument} Candidate: {top_candidate['spec']['id']} Score: {top_candidate['score']:.2f}")

            if top_candidate["eligible"]:
                if store.should_promote(top_candidate["score"], top_candidate["metrics"], instrument):
                    logger.info(f"Promoting new {instrument} Champion!")
                    store.save_new_champion(
                        top_candidate["spec"],
                        top_candidate["metrics"],
                        top_candidate["score"],
                        run_ts,
                        instrument
                    )
                else:
                    logger.info(f"Top {instrument} candidate did not beat current champion.")
            else:
                logger.info(f"Top {instrument} candidate not eligible for champion status.")


    # Save Metrics CSV (Combined)
    all_results.sort(key=lambda x: x["score"], reverse=True)
    csv_data = []
    for r in all_results:
        m = r["metrics"]
        row = {
            "instrument": r["instrument"],
            "id": r["spec"]["id"],
            "score": r["score"],
            "eligible": r["eligible"],
            "sharpe": m.get("sharpe", 0),
            "calmar": m.get("calmar", 0),
            "cagr": m.get("cagr", 0),
            "max_dd": m.get("max_dd", 0),
            "trades": m.get("total_trades", 0),
            "strategy_type": r["spec"]["strategy_type"]
        }
        csv_data.append(row)

    pd.DataFrame(csv_data).to_csv(f"{results_dir}/metrics.csv", index=False)

    # Generate Leaderboard Markdown (Top 20 Total, showing Instrument)
    top_n = min(len(all_results), 20)
    lb_md = "# Strategy Foundry Leaderboard\n\n"
    lb_md += f"Run: {run_ts}\n\n"
    lb_md += "| Rank | Instrument | ID | Score | Sharpe | CAGR | MaxDD | Trades | Type |\n"
    lb_md += "|---|---|---|---|---|---|---|---|---|\n"

    for i in range(top_n):
        r = all_results[i]
        m = r["metrics"]
        lb_md += f"| {i+1} | {r['instrument']} | {r['spec']['id'][:8]} | {r['score']:.1f} | {m.get('sharpe',0):.2f} | {m.get('cagr',0):.1%} | {m.get('max_dd',0):.1%} | {m.get('total_trades',0)} | {r['spec']['strategy_type']} |\n"

    with open("packages/strategy_foundry/results/leaderboard.md", "w") as f:
        f.write(lb_md)

    # 7. Publish Signal
    if not fast_mode:
        publisher = SignalPublisher()
        publisher.publish() # SignalPublisher needs to be updated to check both instruments
        logger.info("Signal publication step completed.")
    else:
        logger.info("Skipping signal publication in FAST_MODE")

if __name__ == "__main__":
    main()
