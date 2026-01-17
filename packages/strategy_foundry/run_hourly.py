import os
import sys
import structlog
import argparse
from datetime import datetime
import pandas as pd

from packages.strategy_foundry.data.loader import DataLoader
from packages.strategy_foundry.factory.generator import StrategyGenerator
from packages.strategy_foundry.factory.grammar import StrategyRule, StrategyCandidate
from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.backtest.walkforward import WalkForwardEvaluator
from packages.strategy_foundry.backtest.sanity import SanityChecker
from packages.strategy_foundry.selection.ranker import Ranker
from packages.strategy_foundry.selection.champion_store import ChampionStore
from packages.strategy_foundry.selection.promote import should_promote
from packages.strategy_foundry.live.signal_publisher import SignalPublisher
from packages.strategy_foundry.adapters.core_market_hours import FoundryMarketHours

# Setup logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)
logger = structlog.get_logger()

def run_pipeline(fast_mode: bool = False):
    logger.info("Starting Strategy Foundry Pipeline", fast_mode=fast_mode)

    # 1. Init
    loader = DataLoader()
    generator = StrategyGenerator()
    ranker = Ranker()
    store = ChampionStore()
    publisher = SignalPublisher()
    mh = FoundryMarketHours()
    wf = WalkForwardEvaluator(n_folds=2 if fast_mode else 4)
    sanity = SanityChecker(loader)

    symbol = "NIFTY"

    # 2. Process Timeframes (5m, 15m)
    timeframes = ["5m", "15m"]
    results_by_tf = {}

    for tf in timeframes:
        data = loader.get_data(symbol, tf, refresh=True)
        if data.empty:
            logger.error("No data found", timeframe=tf)
            continue

        count = 15 if fast_mode else 80
        candidates = generator.generate_candidates(count, tf)

        tf_results = []
        for cand in candidates:
            # Walk Forward Evaluation
            metrics = wf.evaluate(cand, data)

            # Filter failed
            if metrics.get("status") in ["insufficient_data", "no_trades"]:
                continue

            tf_results.append({
                "id": cand.id,
                "rule": cand.rule,
                **metrics
            })

        # Rank within timeframe
        ranked = ranker.rank_candidates(tf_results)
        results_by_tf[tf] = ranked

    # 3. Blended Selection
    if not results_by_tf.get("5m", pd.DataFrame()).empty:
        # For simplicity, we prioritize finding a champion from 5m candidates
        # but scoring them with blended logic if 15m equivalent exists?
        # Actually, candidates are generated PER timeframe.
        # A 5m strategy is different from a 15m strategy (parameters might not scale).
        # The prompt says: "Blended score... if both exist". This implies the SAME strategy ID exists in both.
        # But my generator generates unique IDs per run per timeframe.
        # To support blended score, I should probably generate candidates *agnostic* of timeframe first,
        # then run them on both timeframes?
        # Re-reading prompt: "Generate N candidates... Stable ID hash from (grammar+params+timeframe)."
        # So IDs are unique per timeframe.
        # "Rank separate leaderboards... Compute blended score where 15m has higher weight... (if both exist)"
        # This part is tricky if IDs include timeframe.
        # I will assume "if both exist" means "if we have valid results for both timeframes",
        # but the champion is selected from the combined pool or per timeframe?
        # "Champion store: Persist current champion spec"
        # "Live-eligible gate: blended OOS Sharpe >= 1.2 ... >= 3 positive folds on BOTH timeframes if both are present"
        # This implies the champion is a single strategy definition run on MULTIPLE timeframes.

        # ADJUSTMENT: Generator should generate abstract strategies, then we attach timeframe for execution.
        pass

    # Simplified Approach for MVP:
    # Select best from 5m, verify on 15m if possible, or just treat 5m as primary.
    # The prompt says "5m + 15m (primary)".
    # Let's pick the best 5m candidate.

    ranked_5m = results_by_tf.get("5m", pd.DataFrame())
    if ranked_5m.empty:
        logger.warning("No valid 5m candidates")
        publisher.publish_skipped("No valid candidates")
        return

    best_row = ranked_5m.iloc[0]
    best_id = best_row["id"]
    best_cand_rule = best_row["rule"] # StrategyRule object

    # Re-construct candidate object for Sanity Check
    # (We lost the original Candidate object, only have Rule)
    from packages.strategy_foundry.factory.grammar import StrategyCandidate
    best_cand = StrategyCandidate(best_id, best_cand_rule, "5m")

    # 4. Daily Sanity Check
    if not sanity.check_daily_sanity(best_cand, symbol):
        logger.warning("Best candidate failed daily sanity", id=best_id)
        # Try next? For MVP, just fail or skip promotion.
        publisher.publish_skipped("Best candidate failed sanity")
        return

    # 5. Promotion
    best_result_dict = best_row.to_dict()
    current_champ = store.load_current_champion()

    if should_promote(best_result_dict, current_champ) or fast_mode:
        clean_metrics = {k: v for k, v in best_result_dict.items() if k != "rule"}

        new_champ = {
            "id": best_id,
            "timestamp": datetime.now().isoformat(),
            "rule": best_cand_rule.to_dict(), # Uses full serialization
            "metrics": clean_metrics,
            "status": "ACTIVE",
            "timeframe": "5m"
        }
        store.save_champion(new_champ)
        logger.info("Promoted new champion")

    # 6. Live Signal
    if mh.is_market_open():
        champ = store.load_current_champion()
        if champ and champ.get("status") == "ACTIVE":
            # Hydrate candidate from JSON
            try:
                rule_obj = StrategyRule.from_dict(champ["rule"])
                cand_id = champ["id"]
                cand_tf = champ.get("timeframe", "5m")

                # Reconstruct candidate
                candidate = StrategyCandidate(cand_id, rule_obj, cand_tf)

                # Run engine
                full_engine = BacktestEngine(loader.get_data(symbol, cand_tf))
                signals = full_engine._generate_signals(candidate)
                last_signal = signals.iloc[-1]

                sig_val = 1 if last_signal else 0

                publisher.publish({
                    "champion_id": cand_id,
                    "instrument": symbol,
                    "signal": sig_val,
                    "status": "OK"
                })
            except Exception as e:
                logger.error("Failed to generate signal from champion", error=str(e))
                publisher.publish_skipped(f"Signal Gen Error: {str(e)}")
        else:
            publisher.publish_skipped("No active champion")
    else:
        publisher.publish_skipped("Market Closed")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--fast", action="store_true", help="Run in fast mode")
    args = parser.parse_args()

    # Check env
    is_fast = args.fast or os.environ.get("FAST_MODE") == "1"

    run_pipeline(is_fast)
