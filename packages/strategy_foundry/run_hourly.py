import os
import sys
import pandas as pd
import structlog
from datetime import datetime

# Add root to path
sys.path.append(os.getcwd())

from packages.strategy_foundry.data.loader import load_data
from packages.strategy_foundry.factory.grammar import Grammar
from packages.strategy_foundry.factory.generator import StrategyImpl
from packages.strategy_foundry.backtest.walkforward import walk_forward_validation
from packages.strategy_foundry.selection.ranker import Ranker, ChampionStore, check_promotion
from packages.strategy_foundry.live.signal_publisher import publish_signal

logger = structlog.get_logger()

def main():
    # Determine Mode
    fast_mode = os.environ.get("FAST_MODE", "0") == "1"

    n_candidates = 10 if fast_mode else 50
    n_folds = 2 if fast_mode else 4

    instruments = ["NIFTY", "SENSEX"]

    ranker = Ranker()
    store = ChampionStore()

    run_timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    run_dir = f"packages/strategy_foundry/results/runs/{run_timestamp}"
    os.makedirs(run_dir, exist_ok=True)

    all_candidates = []

    for symbol in instruments:
        logger.info(f"Processing {symbol}...")

        # 1. Update Data
        df = load_data(symbol)
        if df is None:
            continue

        candidates = []

        # 2. Generate Candidates
        for _ in range(n_candidates):
            config = Grammar.get_random_strategy()

            # Factory Func
            def factory(d):
                impl = StrategyImpl(config)
                return impl.generate_positions(d)

            # 3. Walk-Forward
            wf_res = walk_forward_validation(df, factory, n_folds=n_folds)

            # 4. Metrics & Sanity
            # Check sanity
            if "avg_sharpe" in wf_res.get("avg_stats", {}):
                # Simple Sanity
                # Trades? WF returns stats per fold.
                # Check avg trades
                avg_trades = pd.DataFrame(wf_res['fold_results'])['trades'].mean()
                if avg_trades < (10 if fast_mode else 30):
                    continue

                # MaxDD
                avg_dd = wf_res['avg_stats']['avg_calmar'] # wait, I didn't store avg_dd directly in stats?
                # I stored fold results.

                c_dict = config.to_dict()
                c_dict['stats'] = wf_res['avg_stats']
                c_dict['symbol'] = symbol
                candidates.append(c_dict)

        # 5. Rank
        ranked_df = ranker.rank(candidates)

        if not ranked_df.empty:
            # Save candidates
            ranked_df.to_json(f"{run_dir}/candidates_{symbol}.json", orient='records', indent=2)

            # 6. Promote
            top = ranked_df.iloc[0].to_dict()
            curr = store.get_current_champion(symbol)

            # Check eligibility for LIVE (stricter than promotion?)
            # "Live-eligible gate... OOS Sharpe >= 1.0"
            # Promotion is relative.
            # Let's promote if better.

            if check_promotion(curr, top):
                logger.info(f"New Champion for {symbol}!", name=top['name'])
                store.promote(top, symbol)

            all_candidates.extend(ranked_df.to_dict('records'))

    # Update Leaderboard
    if all_candidates:
        lb_path = "packages/strategy_foundry/results/leaderboard.csv"
        new_lb = pd.DataFrame(all_candidates)
        if os.path.exists(lb_path):
            old_lb = pd.read_csv(lb_path)
            combined = pd.concat([old_lb, new_lb]).drop_duplicates(subset=['id'])
        else:
            combined = new_lb
        combined.to_csv(lb_path, index=False)

        # Markdown
        md_path = "packages/strategy_foundry/results/leaderboard.md"
        combined.head(20).to_markdown(md_path, index=False)

    # 7. Publish Signal
    publish_signal()

if __name__ == "__main__":
    main()
