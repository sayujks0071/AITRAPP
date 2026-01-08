import os
import sys
import pandas as pd
import datetime
import pytz
from pathlib import Path
import structlog
import argparse

# Fix python path to allow imports from packages
sys.path.append(os.getcwd())

from packages.strategy_foundry.data.loader import DataLoader
from packages.strategy_foundry.factory.generator import StrategyGenerator
from packages.strategy_foundry.factory.registry import CandidateRegistry
from packages.strategy_foundry.adapters.core_indicators import compute_indicators
from packages.strategy_foundry.backtest.walkforward import WalkForwardEvaluator
from packages.strategy_foundry.backtest.sanity import check_sanity
from packages.strategy_foundry.selection.ranker import rank_candidates
from packages.strategy_foundry.selection.champion_store import ChampionStore
from packages.strategy_foundry.selection.promote import should_promote
from packages.strategy_foundry.live.signal_publisher import SignalPublisher

logger = structlog.get_logger(__name__)
IST = pytz.timezone("Asia/Kolkata")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fast", action="store_true", help="Force fast mode")
    args = parser.parse_args()

    # Env override
    fast_mode = args.fast or os.environ.get("FAST_MODE", "0") == "1"

    run_timestamp = datetime.datetime.now(IST).strftime("%Y%m%d_%H%M%S")
    base_dir = Path("packages/strategy_foundry")
    results_dir = base_dir / "results" / "runs" / run_timestamp
    results_dir.mkdir(parents=True, exist_ok=True)

    loader = DataLoader(base_dir / "data" / "cache")

    instruments = ["NIFTY", "SENSEX"]

    # Run for each instrument
    for instrument in instruments:
        logger.info(f"Starting run for {instrument}", fast_mode=fast_mode)

        # 1. Load Data
        df = loader.get_history(instrument)
        if df.empty:
            logger.error(f"No data for {instrument}")
            continue

        # Compute indicators once? No, strategy might need specific params.
        # But we have a "VectorizedIndicators" adapter that computes a standard set.
        # Our strategies (SimpleTrend) expect 'ema_X' etc.
        # We should pre-compute the SUPERSET of indicators to save time.
        # Our `compute_indicators` does exactly that.
        df_ind = compute_indicators(df)

        # Remove partial today if exists (for stable backtest)
        # Assuming last row is today and market is open?
        # Safe bet: If last row date is today, drop it.
        now = datetime.datetime.now(IST).date()
        if df_ind.index[-1].date() == now:
            # But wait, for Live Signal we might want it?
            # No, we execute at Open. Signal comes from Prev Close.
            # So we don't need Today's data for Today's Signal.
            df_backtest = df_ind.iloc[:-1]
        else:
            df_backtest = df_ind

        # 2. Generate Candidates
        count = 10 if fast_mode else 50
        gen = StrategyGenerator(count)
        candidates = gen.generate()

        # 3. Evaluate
        folds = 2 if fast_mode else 4
        evaluator = WalkForwardEvaluator(folds)

        results = []
        for strat in candidates:
            # Backtest
            metrics = evaluator.evaluate(strat, df_backtest)

            # Sanity
            sanity = check_sanity(metrics, fast_mode)

            if sanity['passed']:
                results.append({
                    "id": strat.get_id(),
                    "params": strat.params,
                    "rule_summary": strat.rule_summary,
                    "metrics": metrics
                })

        # 4. Rank
        ranked_df = rank_candidates(results)

        # Save results
        ranked_df.to_csv(results_dir / f"candidates_{instrument}.csv", index=False)

        # 5. Champion Selection
        champ_store = ChampionStore(base_dir / "results" / "champions" / instrument)
        champ_store.history_dir.mkdir(parents=True, exist_ok=True) # Ensure dir exists

        current_champ = champ_store.load_champion()

        if not ranked_df.empty and not fast_mode:
            top_candidate = ranked_df.iloc[0].to_dict()

            if should_promote(top_candidate, current_champ):
                champ_store.promote_champion(top_candidate, run_timestamp)
                current_champ = champ_store.load_champion()
        elif fast_mode:
            logger.info("Fast mode active: skipping promotion")

        # 6. Publish Signal (using current champ)
        publisher = SignalPublisher(base_dir / "results")
        if current_champ:
            # Re-instantiate strategy
            from packages.strategy_foundry.factory.registry import CandidateRegistry
            # We can use the registry's load logic logic or just direct init
            # But we don't have a direct "from_dict" factory easy access here without import loops
            # Let's simple-init based on type
            params = current_champ['params']
            stype = params.get('type')
            strat = None
            if stype == "SimpleTrend":
                from packages.strategy_foundry.factory.grammar import SimpleTrendStrategy
                strat = SimpleTrendStrategy(params)
            elif stype == "MeanReversion":
                from packages.strategy_foundry.factory.grammar import MeanReversionStrategy
                strat = MeanReversionStrategy(params)

            if strat:
                # Generate signal on data up to T-1
                # df_backtest ends at T-1
                positions = strat.generate_positions(df_backtest)
                # Signal for T is the LAST value
                if not positions.empty:
                    signal = int(positions.iloc[-1])
                    publisher.publish(current_champ, signal, instrument)
                else:
                    logger.warning("Empty positions for champion")

    # Update Leaderboard MD
    # (Simple append or overwrite)
    # We can write a summary MD
    with open(base_dir / "results" / "leaderboard.md", "w") as f:
        f.write(f"# Leaderboard (Run {run_timestamp})\n\n")
        f.write("## NIFTY Top 5\n")
        nifty_res = results_dir / "candidates_NIFTY.csv"
        if nifty_res.exists():
            try:
                df = pd.read_csv(nifty_res)
                if not df.empty:
                    f.write(df.head(5).to_markdown())
                else:
                    f.write("No candidates passed.")
            except pd.errors.EmptyDataError:
                f.write("No candidates passed.")

        f.write("\n\n## SENSEX Top 5\n")
        sensex_res = results_dir / "candidates_SENSEX.csv"
        if sensex_res.exists():
            try:
                df = pd.read_csv(sensex_res)
                if not df.empty:
                    f.write(df.head(5).to_markdown())
                else:
                    f.write("No candidates passed.")
            except pd.errors.EmptyDataError:
                f.write("No candidates passed.")

if __name__ == "__main__":
    main()
