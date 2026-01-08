"""
Main Hourly Runner.
"""
import os
import sys
import structlog
import pandas as pd
from datetime import datetime
import json

# Ensure path for imports
sys.path.append(os.getcwd())

from packages.strategy_foundry.configs.config import load_foundry_config
from packages.strategy_foundry.data.loader import DataLoader
from packages.strategy_foundry.factory.generator import StrategyGenerator
from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.backtest.walkforward import WalkForwardValidator
from packages.strategy_foundry.backtest.sanity import SanityChecker
from packages.strategy_foundry.selection.ranker import Ranker
from packages.strategy_foundry.selection.champion_store import ChampionStore
from packages.strategy_foundry.selection.promote import Promoter
from packages.strategy_foundry.live.signal_publisher import SignalPublisher

logger = structlog.get_logger(__name__)

def main():
    config = load_foundry_config()
    is_fast_mode = os.environ.get("FAST_MODE", "0") == "1"

    logger.info("Starting Hourly Foundry Run", fast_mode=is_fast_mode)

    # 1. Data
    loader = DataLoader()
    instruments = ["NIFTY"] # TODO: config
    timeframes = ["5m", "15m"] if not is_fast_mode else ["5m"]

    data_map = {}
    for inst in instruments:
        for tf in timeframes:
            df = loader.get_data(inst, tf, days=60)
            data_map[(inst, tf)] = df

        # Load 1D for Sanity
        data_map[(inst, "1d")] = loader.get_data(inst, "1d", days=365*2)

    # 2. Components
    generator = StrategyGenerator()
    engine = BacktestEngine()
    ranker = Ranker()
    validator = WalkForwardValidator(engine, ranker, folds=4, is_fast_mode=is_fast_mode)
    sanity = SanityChecker(engine, ranker)
    store = ChampionStore()
    promoter = Promoter()

    results = []
    num_candidates = 15 if is_fast_mode else 80

    # 3. Research Loop
    for inst in instruments:
        for tf in timeframes:
            df = data_map.get((inst, tf))
            if df is None or df.empty:
                continue

            # Generate
            candidates = generator.generate_candidates(num_candidates, tf)

            for cand in candidates:
                # Walk-Forward Validation
                res = validator.validate(cand, df)
                if not res["valid"]:
                    continue

                metrics = res["metrics"]

                # Pre-filter (Intraday Robustness)
                if not sanity.check_intraday_robustness(metrics, config):
                    continue

                # Daily Sanity Check
                daily_df = data_map.get((inst, "1d"))
                if not sanity.check_daily_sanity(cand, daily_df):
                    continue

                # Passed
                results.append({
                    "candidate": cand,
                    "metrics": metrics,
                    "instrument": inst,
                    "timeframe": tf
                })

    # 4. Ranking
    filtered = results # Already filtered by sanity
    for r in filtered:
        r["score"] = ranker.score(r["metrics"])

    filtered.sort(key=lambda x: x["score"], reverse=True)

    # 5. Promotion
    incumbent = store.load_champion()

    # Check top challenger
    best_challenger = filtered[0] if filtered else None

    new_champion = None
    if best_challenger:
        if is_fast_mode:
             logger.info("FAST_MODE: Skipping promotion")
             # In fast mode, we don't promote, but for demo/testing we might want to see signal.
             # Let's say we don't overwrite champion, but we use best_challenger for signal if no champion exists.
             if incumbent is None:
                 new_champion = best_challenger
                 # Don't save to disk in FAST_MODE usually, but here we might want to test flow.
             else:
                 new_champion = incumbent
        else:
             if promoter.should_promote(best_challenger, incumbent):
                 new_champion = best_challenger
                 store.save_champion(new_champion)
                 logger.info("NEW CHAMPION PROMOTED", id=new_champion["candidate"].id)
             else:
                 new_champion = incumbent
                 logger.info("Incumbent retained")
    else:
        new_champion = incumbent

    # 6. Live Signal
    publisher = SignalPublisher()

    signal = 0
    if new_champion:
        c_inst = new_champion["instrument"]
        c_tf = new_champion["timeframe"]
        c_df = data_map.get((c_inst, c_tf))

        if c_df is not None and not c_df.empty:
            # Re-run specifically to get latest signal
            engine._prepare_indicators(c_df, new_champion["candidate"])
            signals = engine._generate_signals(c_df, new_champion["candidate"])
            if not signals.empty:
                 signal = int(signals.iloc[-1])

    publisher.publish(
        champion=new_champion["candidate"].__dict__ if new_champion else None,
        signal=signal,
        reason="Champion Active" if new_champion else "No Champion"
    )

    logger.info("Foundry Run Complete")

if __name__ == "__main__":
    main()
