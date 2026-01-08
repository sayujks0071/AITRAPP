"""
Strategy Foundry Hourly Runner
Main entry point for the hourly workflow.
"""
import os
import sys
import yaml
import json
import structlog
import pandas as pd
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.append(os.getcwd())

from packages.strategy_foundry.data.loader import DataLoader
from packages.strategy_foundry.factory.generator import StrategyGenerator, StrategyConfig
from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.backtest.walkforward import WalkForward
from packages.strategy_foundry.backtest.metrics import BacktestMetrics
from packages.strategy_foundry.backtest.sanity import SanityChecker
from packages.strategy_foundry.selection.ranker import Ranker
from packages.strategy_foundry.selection.champion_store import ChampionStore
from packages.strategy_foundry.selection.promote import Promoter
from packages.strategy_foundry.live.signal_publisher import SignalPublisher
from packages.strategy_foundry.adapters.core_market_hours import MarketHoursGuard, IST

logger = structlog.get_logger(__name__)

# Configs
CONFIG_PATH = Path("packages/strategy_foundry/configs/foundry.yaml")
INSTRUMENT_MAP_PATH = Path("packages/strategy_foundry/configs/instrument_map.yaml")

def load_config():
    with open(CONFIG_PATH, 'r') as f:
        return yaml.safe_load(f)

def load_instrument_map():
    with open(INSTRUMENT_MAP_PATH, 'r') as f:
        return yaml.safe_load(f)

def main():
    logger.info("Starting Strategy Foundry Hourly Run")

    # 0. Setup
    config = load_config()
    instrument_map = load_instrument_map()

    fast_mode = os.environ.get("FAST_MODE", "0") == "1"
    run_ts = datetime.now(IST).strftime("%Y%m%d_%H%M%S")

    results_dir = Path(f"packages/strategy_foundry/results/runs/{run_ts}")
    results_dir.mkdir(parents=True, exist_ok=True)

    loader = DataLoader()
    mh_guard = MarketHoursGuard()

    # 1. Generate Candidates
    n_candidates = config['defaults']['fast_mode_candidates'] if fast_mode else config['defaults']['max_candidates']
    candidates = StrategyGenerator.generate_population(n_candidates)

    # Save candidates
    with open(results_dir / "candidates.json", 'w') as f:
        json.dump([c.__dict__ for c in candidates], f, indent=2, default=str)

    all_results = []

    # 2. Loop over instruments and timeframes
    # For MVP, focus on NIFTY 5m and 15m
    research_symbol = instrument_map['research']['NIFTY']

    for tf in config['defaults']['timeframes']:
        if tf == "1d": continue # Skip 1d for training, used for sanity

        logger.info(f"Processing {research_symbol} {tf}")

        # Load Data
        df = loader.get_data(research_symbol, tf)
        if df.empty or len(df) < 500:
            logger.warning(f"Not enough data for {tf}")
            continue

        # Walk-Forward Cross Validation
        n_folds = config['defaults']['fast_mode_folds'] if fast_mode else config['defaults']['folds']
        splits = WalkForward.split(df, folds=n_folds)

        if not splits:
            continue

        for cand in candidates:
            fold_metrics = []

            for train_df, test_df in splits:
                # Test on OOS
                test_engine = BacktestEngine(test_df)
                trades, equity = test_engine.run(cand)
                metrics = BacktestMetrics.calculate(trades, equity)
                fold_metrics.append(metrics)

            # Aggregate OOS metrics
            if not fold_metrics:
                continue

            avg_sharpe = sum(m['sharpe'] for m in fold_metrics) / len(fold_metrics)
            avg_calmar = sum(m['calmar'] for m in fold_metrics) / len(fold_metrics)
            avg_cagr = sum(m['cagr'] for m in fold_metrics) / len(fold_metrics)
            max_dd = max(m['max_drawdown'] for m in fold_metrics) # Conservative: take max DD

            positive_folds = sum(1 for m in fold_metrics if m['net_profit'] > 0)

            agg_metrics = {
                "sharpe": avg_sharpe,
                "calmar": avg_calmar,
                "cagr": avg_cagr,
                "max_drawdown": max_dd,
                "positive_folds": positive_folds,
                "total_trades": sum(m['total_trades'] for m in fold_metrics),
                "profit_factor": sum(m['profit_factor'] for m in fold_metrics) / len(fold_metrics),
                "net_profit": sum(m['net_profit'] for m in fold_metrics)
            }

            # Score
            score = Ranker.calculate_score(agg_metrics, config['weights'])

            all_results.append({
                "id": cand.id,
                "config": cand.__dict__,
                "metrics": agg_metrics,
                "score": score,
                "timeframe": tf,
                "instrument": "NIFTY"
            })

    # 3. Ranking & Selection with Blended Score and Sanity Checks

    # Convert to DataFrame
    df_results = pd.DataFrame(all_results)

    ranked_df = pd.DataFrame() # Initialize empty

    if not df_results.empty:
        # Calculate Blended Score if multiple timeframes exist
        pivot = df_results.pivot(index='id', columns='timeframe', values='score')

        if '5m' in pivot.columns and '15m' in pivot.columns:
            pivot['blended_score'] = pivot.apply(
                lambda x: (0.6 * x['15m'] + 0.4 * x['5m']) if pd.notna(x['15m']) and pd.notna(x['5m'])
                else (x['15m'] if pd.notna(x['15m']) else x['5m']), axis=1
            )
        elif '15m' in pivot.columns:
            pivot['blended_score'] = pivot['15m']
        elif '5m' in pivot.columns:
            pivot['blended_score'] = pivot['5m']
        else:
            pivot['blended_score'] = 0

        pivot = pivot.sort_values('blended_score', ascending=False)

        ranked_results = []
        for cid in pivot.index:
            rows = df_results[df_results['id'] == cid]
            if rows.empty: continue

            # Pick representative row
            row_15m = rows[rows['timeframe'] == '15m']
            row_5m = rows[rows['timeframe'] == '5m']

            if not row_15m.empty and not row_5m.empty:
                 # Prefer 15m as base if score is better there, else 5m
                 # Logic: Use the timeframe that has the higher score contribution?
                 # Or default to 15m for robustness.
                 if row_15m.iloc[0]['score'] >= row_5m.iloc[0]['score']:
                     rep = row_15m.iloc[0]
                 else:
                     rep = row_5m.iloc[0]
            elif not row_15m.empty:
                rep = row_15m.iloc[0]
            else:
                rep = row_5m.iloc[0]

            res_dict = rep.to_dict()
            res_dict['score'] = pivot.loc[cid, 'blended_score']
            ranked_results.append(res_dict)

        ranked_df = pd.DataFrame(ranked_results)

        # Daily Sanity Overlay
        final_candidates = []
        df_daily = loader.get_data(research_symbol, "1d")

        for i, row in ranked_df.head(15).iterrows():
            if not df_daily.empty and len(df_daily) > 200:
                 sanity_engine = BacktestEngine(df_daily)
                 config_obj = StrategyConfig(**row['config'])
                 t_sanity, e_sanity = sanity_engine.run(config_obj)
                 m_sanity = BacktestMetrics.calculate(t_sanity, e_sanity)

                 if not SanityChecker.check_daily_sanity(m_sanity):
                     logger.info(f"Candidate {row['id']} failed daily sanity check", metrics=m_sanity)
                     continue

            final_candidates.append(row)
            if len(final_candidates) >= 10:
                break

        ranked_df = pd.DataFrame(final_candidates)

    if ranked_df.empty:
        logger.warning("No results after ranking and sanity checks")
    else:
        # Save full results
        ranked_df.to_csv(results_dir / "metrics.csv")

        # Generate Leaderboard Markdown
        top_10 = ranked_df.head(10)
        with open(results_dir / "leaderboard.md", 'w') as f:
            f.write(top_10.to_markdown())

    # 4. Champion Promotion (Full Mode Only)
    champion_store = ChampionStore()
    current_champ_data = champion_store.load_current()

    if not fast_mode and not ranked_df.empty:
        best_candidate = ranked_df.iloc[0].to_dict()

        min_folds = config['thresholds']['min_positive_folds']
        if best_candidate['metrics']['positive_folds'] >= min_folds:

            if Promoter.should_promote(best_candidate, current_champ_data.get('metrics')):
                logger.info(f"Promoting new champion: {best_candidate['id']}")
                champion_store.save_new_champion(
                    best_candidate['config'],
                    best_candidate['metrics'],
                    best_candidate['timeframe'],
                    run_ts
                )
                current_champ_data = {
                    "strategy": best_candidate['config'],
                    "metrics": best_candidate['metrics'],
                    "timeframe": best_candidate['timeframe']
                }

    # 5. Live Signal Publishing
    if mh_guard.is_market_open():
        if not current_champ_data:
             SignalPublisher.publish_skipped("No champion available")
        else:
            tf = current_champ_data.get('timeframe', "5m")
            champ_config = StrategyConfig(**current_champ_data['strategy'])

            # Use live proxy or research symbol?
            # We need data to calculate signal. Research symbol is what we have data for.
            # Ideally we download fresh data for research symbol.

            df = loader.get_data(research_symbol, tf, force_refresh=True)

            if df.empty:
                SignalPublisher.publish_skipped("Live data fetch failed")
            else:
                engine = BacktestEngine(df)
                entries = engine._generate_entries(df, champ_config)

                # Signal is the last entry value.
                # If entries[-1] is 1, it means at the CLOSE of the last bar, we got a buy signal.
                # Executable at the OPEN of the NEXT bar (now).

                last_signal = entries.iloc[-1]

                signal_val = 0
                if last_signal == 1:
                    signal_val = 1
                elif last_signal == -1:
                    signal_val = -1

                # Wait, if we are already in a trade?
                # The prompt says "Signal calculated on bar close... execute next bar open".
                # It doesn't ask for full position management in the signal JSON, just the signal.
                # "signal": -1|0|1

                SignalPublisher.publish({
                    "champion_id": champ_config.id,
                    "timeframe": tf,
                    "instrument": "NIFTY",
                    "proxy_symbol_paper": instrument_map['paper_proxy']['NIFTY'],
                    "proxy_symbol_live": instrument_map['live_proxy']['NIFTY'],
                    "signal": int(signal_val),
                    "rule_summary": f"{champ_config.entry_block} + {champ_config.exit_block}",
                    "risk": {
                        "stop": champ_config.risk_block,
                        "params": champ_config.risk_params,
                        "flat_by": config['defaults']['flat_time']
                    },
                    "status": "OK"
                })
    else:
        SignalPublisher.publish_skipped("Market Closed")

if __name__ == "__main__":
    main()
