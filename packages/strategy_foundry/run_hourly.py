"""Hourly Runner"""
import os
import sys
import argparse
import structlog
from datetime import datetime
import pandas as pd
import json

from packages.strategy_foundry.data.loader import DataLoader
from packages.strategy_foundry.factory.generator import StrategyGenerator, StrategyCandidate
from packages.strategy_foundry.factory.factory import StrategyFactory
from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.backtest.walkforward import WalkForwardEvaluator
from packages.strategy_foundry.backtest.sanity import check_sanity
from packages.strategy_foundry.selection.ranker import calculate_score
from packages.strategy_foundry.selection.champion_store import ChampionStore
from packages.strategy_foundry.selection.promote import should_promote
from packages.strategy_foundry.adapters.core_market_hours import MarketHoursAdapter
from packages.strategy_foundry.live.signal_publisher import SignalPublisher

logger = structlog.get_logger(__name__)

def run():
    # 0. Config
    FAST_MODE = os.getenv("FAST_MODE", "0") == "1"
    run_ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 1. Setup
    loader = DataLoader()
    generator = StrategyGenerator()
    wf_eval = WalkForwardEvaluator(folds=2 if FAST_MODE else 3)
    champ_store = ChampionStore()
    publisher = SignalPublisher()
    market = MarketHoursAdapter()

    results_dir = f"packages/strategy_foundry/results/runs/{run_ts}"

    for SYMBOL in ["NIFTY", "SENSEX"]:
        logger.info(f"--- Processing {SYMBOL} ---")

        # 2. Update Data
        try:
            df = loader.get_data(SYMBOL)
        except Exception as e:
            logger.error("Data update failed", error=str(e), symbol=SYMBOL)
            publisher.publish_skipped(f"Data update failed for {SYMBOL}: {e}")
            continue

        if df.empty:
            logger.warning("Empty data", symbol=SYMBOL)
            continue

        # 3. Generate Candidates
        count = 10 if FAST_MODE else 50
        candidates = generator.generate(n=count)

        # 4. Evaluate Candidates
        results = []

        for cand in candidates:
            # Full backtest for sanity
            be = BacktestEngine(allow_short=False)
            try:
                bt_res = be.run(df, cand)
            except Exception as e:
                logger.debug("Backtest crash", error=str(e))
                continue

            # Sanity Check
            passed, reason = check_sanity(bt_res['metrics'], FAST_MODE)
            if not passed:
                continue

            # Walk Forward
            oos_stats = wf_eval.evaluate(df, cand)
            if not oos_stats:
                continue

            score = calculate_score(oos_stats)

            results.append({
                "candidate": cand,
                "metrics": bt_res['metrics'],
                "oos_metrics": oos_stats,
                "score": score
            })

        # Sort by score
        results.sort(key=lambda x: x['score'], reverse=True)

        # 5. Champion Selection
        current_champ_data = champ_store.load_current(symbol=SYMBOL)
        final_champion = current_champ_data
        promoted = False
        best_new = None

        if results:
            best_new = results[0]
            if current_champ_data:
                # Compare
                curr_score = current_champ_data.get('score', 0)
                curr_dd = current_champ_data.get('oos_metrics', {}).get('oos_max_dd', 1.0)

                new_score = best_new['score']
                new_dd = best_new['oos_metrics']['oos_max_dd']

                if should_promote(new_score, curr_score, new_dd, curr_dd):
                    promoted = True
            else:
                # No current champion, promote best new
                promoted = True
        else:
            logger.warning("No valid candidates found", symbol=SYMBOL)

        if promoted and best_new:
            logger.info("Promoting new champion", symbol=SYMBOL, id=best_new['candidate'].id, score=best_new['score'])

            # Serialize candidate
            champ_dict = {
                "id": best_new['candidate'].id,
                "rules": best_new['candidate'].to_dict(),
                "score": best_new['score'],
                "metrics": best_new['metrics'],
                "oos_metrics": best_new['oos_metrics'],
                "timestamp": run_ts,
                "symbol": SYMBOL
            }
            champ_store.save_new(champ_dict, run_ts, symbol=SYMBOL)
            final_champion = champ_dict
        elif not results and not final_champion:
             # No candidates and no old champion
             pass
        else:
            logger.info("Keeping current champion", symbol=SYMBOL)

        # 6. Live Signal Generation
        active_candidate = None
        if promoted and best_new:
            active_candidate = best_new['candidate']
        elif final_champion:
            try:
                active_candidate = StrategyFactory.from_dict(final_champion['rules'])
            except Exception as e:
                logger.error("Failed to reconstruct champion", error=str(e))

        # Publish logic
        if active_candidate and market.is_market_open():
            # Get latest signal
            indicators = be._calc_indicators(df)
            signals = active_candidate.generate_positions(df, indicators)

            # Last signal (scalar)
            last_sig = signals.iloc[-1]

            publisher.publish(
                signal=last_sig,
                instrument=SYMBOL,
                champion=final_champion,
                status="OK"
            )
        elif not active_candidate:
             publisher.publish_skipped(f"No active champion for {SYMBOL}")
        else:
            publisher.publish_skipped("Market Closed")

        # 7. Artifacts
        if results:
            os.makedirs(results_dir, exist_ok=True)
            top_10 = []
            for r in results[:10]:
                top_10.append({
                    "id": r['candidate'].id,
                    "score": r['score'],
                    "cagr": r['metrics']['cagr'],
                    "sharpe": r['metrics']['sharpe'],
                    "rules": r['candidate'].to_dict()
                })

            pd.DataFrame(top_10).to_csv(f"{results_dir}/leaderboard_{SYMBOL}.csv")

if __name__ == "__main__":
    run()
