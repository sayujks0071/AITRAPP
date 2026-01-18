"""
Hourly Runner for Strategy Foundry.
"""
import os
import sys
import structlog
import pandas as pd
from datetime import datetime
import json
import pytz

# Add repo root to path
sys.path.append(os.getcwd())

from packages.strategy_foundry.data.loader import DataLoader
from packages.strategy_foundry.adapters.core_indicators import VectorIndicatorCalculator
from packages.strategy_foundry.factory.generator import StrategyGenerator
from packages.strategy_foundry.factory.grammar import StrategyCandidate
from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.backtest.metrics import compute_metrics
from packages.strategy_foundry.selection.ranker import Ranker
from packages.strategy_foundry.selection.champion_store import ChampionStore
from packages.strategy_foundry.live.signal_publisher import SignalPublisher

logger = structlog.get_logger(__name__)

def main():
    logger.info("Starting Strategy Foundry Hourly Run")

    # 1. Config
    fast_mode = os.environ.get("FAST_MODE", "0") == "1"
    n_candidates = 10 if fast_mode else 50
    instruments = ["NIFTY", "SENSEX"]

    # Run ID
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = f"packages/strategy_foundry/results/runs/{timestamp}"
    os.makedirs(run_dir, exist_ok=True)

    # 2. Load Data
    loader = DataLoader()
    dfs = {}
    indicators = {}

    calc = VectorIndicatorCalculator()

    for inst in instruments:
        try:
            df = loader.get_data(inst)
            dfs[inst] = df
            # Precompute Indicators
            indicators[inst] = calc.compute_vectors(df)
            logger.info(f"Loaded {inst}: {len(df)} bars")
        except Exception as e:
            logger.error(f"Failed to load {inst}: {e}")

    if not dfs:
        logger.error("No data available. Exiting.")
        return

    # 3. Generate Candidates
    gen = StrategyGenerator()
    candidates = gen.generate_candidates(n=n_candidates)

    # Save Candidates
    cand_list = [c.to_json() for c in candidates]
    with open(f"{run_dir}/candidates.json", "w") as f:
        json.dump(cand_list, f, indent=2)

    # 4. Backtest Loop
    engine = BacktestEngine()
    results = []

    for cand in candidates:
        for inst, df in dfs.items():
            ind = indicators[inst]
            try:
                bt_res = engine.run(df, cand, ind)
                metrics = compute_metrics(bt_res["trades"], bt_res["equity"])

                res_row = metrics.copy()
                res_row["id"] = cand.strategy_id
                res_row["instrument"] = inst
                results.append(res_row)
            except Exception as e:
                logger.error(f"Backtest failed for {cand.strategy_id} on {inst}: {e}")

    results_df = pd.DataFrame(results)
    results_df.to_csv(f"{run_dir}/metrics.csv", index=False)

    # 5. Rank & Select
    ranker = Ranker()
    ranked = ranker.rank(results_df)

    leader = ranked.iloc[0] if not ranked.empty else None

    # 6. Champion Logic
    store = ChampionStore()
    curr_champ = store.get_current_champion()

    # Logic: If leader score > current * 1.1 => Promote
    # Need to store score in champion JSON

    if leader is not None and leader["score"] > 0: # Sanity
        # Fetch candidate obj
        champ_cand = next(c for c in candidates if c.strategy_id == leader["id"])

        should_promote = False
        if not curr_champ:
            should_promote = True
        else:
            prev_score = curr_champ["metrics"].get("score", 0)
            if leader["score"] > prev_score * 1.1:
                should_promote = True

        if should_promote:
            store.promote_new_champion(
                champ_cand.to_json(),
                leader.to_dict(),
                timestamp
            )
            curr_champ = store.get_current_champion()

    # 7. Live Signal (Simulation)
    publisher = SignalPublisher()

    if curr_champ:
        # Evaluate current champion on LATEST data (already done in loop? No)
        # We need to run the specific champion on the specific instrument it is good at.
        # Ideally, we have separate champions for NIFTY vs SENSEX.
        # For simplicity, we just take the global best.

        c_inst = curr_champ["metrics"]["instrument"]
        if c_inst in dfs:
            c_cand = StrategyCandidate.from_json(curr_champ["candidate"])

            # Re-run to get latest signal
            # Optimization: generate only last bar?
            # We need indicators.
            df = dfs[c_inst]
            ind = indicators[c_inst]

            # Generate positions
            signals = c_cand.generate_positions(df, ind)

            # Last completed bar signal
            # "Execution: next-bar open".
            # So if we are running at 10:00 (hourly), we check the last completed daily bar?
            # This is a DAILY strategy lab.
            # So we check the signal for TODAY (based on yesterday close).

            # If we run intraday, we might have intraday bars?
            # But we are using Daily Data from Yahoo.
            # So the signal is valid for "Today's Open".
            # If we run at 10AM, the signal was generated yesterday.

            latest_signal = int(signals.iloc[-1]) # This is signal based on close[-1]
            # This signal is for T+1.
            # Since close[-1] is "Yesterday" (if we fetch daily data before today close).
            # Yahoo daily data usually updates EOD.
            # So fetching during market hours gives yesterday's data as last row.

            publisher.publish(curr_champ, latest_signal, c_inst)

    logger.info("Run Complete", leader_id=leader["id"] if leader is not None else "None")

if __name__ == "__main__":
    main()
