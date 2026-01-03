import os
import argparse
import structlog
from pathlib import Path
from datetime import datetime, time
import pandas as pd
import pytz

from packages.strategy_foundry.data.loader import DataLoader
from packages.strategy_foundry.adapters.core_indicators import calculate_indicators
from packages.strategy_foundry.factory.generator import StrategyGenerator
from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.backtest.metrics import compute_metrics
from packages.strategy_foundry.selection.ranker import Ranker
from packages.strategy_foundry.live.signal_publisher import SignalPublisher

logger = structlog.get_logger(__name__)

def is_market_open() -> bool:
    """
    Check if NSE market is open (09:15 - 15:30 IST).
    """
    tz = pytz.timezone('Asia/Kolkata')
    now = datetime.now(tz)

    # Weekends
    if now.weekday() >= 5:
        return False

    current_time = now.time()
    market_start = time(9, 15)
    market_end = time(15, 30)

    return market_start <= current_time <= market_end

def run_instrument(instrument: str, fast_mode: bool, loader: DataLoader, results_dir: Path):
    logger.info(f"Processing {instrument}")

    # 1. Load Data
    df_15m = loader.get_data(instrument, "15m")
    df_5m = loader.get_data(instrument, "5m")
    df_1d = loader.get_data(instrument, "1d")

    if df_15m.empty or df_5m.empty:
        logger.error(f"No intraday data available for {instrument}. Skipping.")
        return

    # Add Indicators
    df_15m = calculate_indicators(df_15m)
    df_5m = calculate_indicators(df_5m)
    if not df_1d.empty:
        df_1d = calculate_indicators(df_1d)

    # 2. Generate Candidates
    gen = StrategyGenerator(instrument=instrument, timeframe="15m")
    count = 10 if fast_mode else 50
    candidates = gen.generate(n=count)

    # 3. Backtest (Walk-Forward / Split)
    split_idx_15 = int(len(df_15m) * 0.7)
    train_15 = df_15m.iloc[:split_idx_15]
    test_15 = df_15m.iloc[split_idx_15:]

    evaluated = []

    for cand in candidates:
        # Backtest on 15m Test (OOS)
        engine_15 = BacktestEngine(test_15, cand)
        res_15 = engine_15.run()
        met_15 = compute_metrics(res_15['trades'])

        # Backtest on 5m
        engine_5 = BacktestEngine(df_5m.iloc[-1000:], cand)
        res_5 = engine_5.run()
        met_5 = compute_metrics(res_5['trades'])

        # 1D Sanity Check
        met_1d = {}
        if not df_1d.empty:
            # We treat 1D as just another backtest.
            # Note: Strategy logic is intraday (EOD exit), but for 1D we might relax EOD exit
            # OR we just check if logic holds on Daily bars (Swing).
            # The prompt says: "Daily sanity overlay... if daily performance is catastrophically negative... reject"
            # Strategy rules (time stops, EOD exits) might not make sense on 1D unless adjusted.
            # But "run 1D sanity backtest" implies running the SAME logic on 1D bars.
            # So "EOD exit" on 1D means "End of Year"? No, EOD means End of Bar usually in intraday ctx.
            # On 1D, "EOD exit" (15:25) check will fail or pass depending on timestamp.
            # Engine logic: `if times[i].hour == 15 and times[i].minute >= 25`.
            # Daily bars usually have 00:00 or 15:30 timestamp.
            # If timestamp is 00:00, EOD logic won't trigger.
            # So it becomes a swing strategy.

            engine_1d = BacktestEngine(df_1d, cand, force_eod_exit=False)
            res_1d = engine_1d.run()
            met_1d = compute_metrics(res_1d['trades'])

        # Sanity Check Logic
        passed_sanity = True
        if met_1d:
            if met_1d['sharpe'] < -0.2 or met_1d['max_dd'] > 0.45:
                passed_sanity = False

        if passed_sanity:
            evaluated.append({
                "candidate": cand,
                "metrics_oos_15m": met_15,
                "metrics_oos_5m": met_5,
                "metrics_1d": met_1d,
                "score": 0 # filled by ranker
            })

    # 4. Rank
    ranker = Ranker()
    ranked = ranker.rank(evaluated)

    # Save Leaderboard
    leaderboard = []
    for r in ranked:
        row = {
            "id": r['candidate'].id,
            "instrument": instrument,
            "score": r['score'],
            "sharpe_15m": r['metrics_oos_15m']['sharpe'],
            "net_15m": r['metrics_oos_15m']['net_return'],
            "dd_15m": r['metrics_oos_15m']['max_dd'],
            "sharpe_5m": r['metrics_oos_5m']['sharpe'],
            "sharpe_1d": r['metrics_1d'].get('sharpe', 0)
        }
        leaderboard.append(row)

    pd.DataFrame(leaderboard).to_csv(results_dir / f"leaderboard_{instrument}.csv", index=False)

    # 5. Select Champion & Publish Live Signal
    if ranked:
        champion = ranked[0]
        logger.info(f"Champion selected for {instrument}: {champion['candidate'].id} Score: {champion['score']}")

        # Check eligibility
        is_eligible = True
        if champion['score'] < 0.5:
            is_eligible = False
            logger.info("Champion score too low, skipping live signal")

        signal = 0
        reason = ""
        status = "SKIPPED"

        if not is_market_open():
             reason = "Market Closed"
        elif is_eligible:
            # Calculate LIVE Signal
            # Run engine on FULL 15m data with force_eod_exit=False (to see if we should hold/enter now)
            # Actually, the logic is:
            # We want to know if we should be Long or Flat RIGHT NOW.

            # Since we run hourly, we might be mid-trade.
            engine_live = BacktestEngine(df_15m, champion['candidate'], force_eod_exit=False)
            res_live = engine_live.run()

            signal = res_live.get('current_signal', 0)
            status = "OK" if signal != 0 else "SKIPPED"
            if signal == 0:
                reason = "No Signal / Flat"
        else:
             reason = "No eligible champion"

        publisher = SignalPublisher(Path("packages/strategy_foundry/results"))
        publisher.publish(champion, signal, reason=reason)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fast", action="store_true", help="Run in fast mode")
    args = parser.parse_args()

    fast_mode = args.fast or os.environ.get("FAST_MODE") == "1"

    run_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_dir = Path(f"packages/strategy_foundry/results/runs/{run_ts}")
    results_dir.mkdir(parents=True, exist_ok=True)

    loader = DataLoader()

    instruments = ["NIFTY", "SENSEX"]

    for instrument in instruments:
        try:
            run_instrument(instrument, fast_mode, loader, results_dir)
        except Exception as e:
            logger.error(f"Failed to process {instrument}", error=str(e))

if __name__ == "__main__":
    main()
