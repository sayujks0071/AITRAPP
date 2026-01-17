import json
import os
import pandas as pd
from datetime import datetime
import pytz
from packages.strategy_foundry.adapters.core_market_hours import MarketAdapter
from packages.strategy_foundry.data.loader import get_data
from packages.strategy_foundry.backtest.engine import BacktestEngine
from packages.strategy_foundry.selection.champion_store import ChampionStore
import structlog

logger = structlog.get_logger(__name__)

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "../results")
os.makedirs(RESULTS_DIR, exist_ok=True)
LIVE_SIGNAL_FILE = os.path.join(RESULTS_DIR, "live_signal.json")

def publish_signal():
    """
    Generate and publish live signal JSON.
    """
    market = MarketAdapter()
    now = datetime.now(pytz.timezone("Asia/Kolkata"))

    # 1. Check Market Hours
    if not market.is_market_open(now):
        _write_skipped("Market Closed")
        return

    # 2. Load Champion
    store = ChampionStore(os.path.join(RESULTS_DIR, "champions"))
    champion = store.load_current()
    if not champion:
        _write_skipped("No Champion")
        return

    # 3. Check Eligibility (Sanity)
    meta = store.load_current_metadata()
    metrics = meta.get('metrics', {})
    if metrics.get('sharpe', 0) < 1.0 or abs(metrics.get('max_drawdown', 1)) > 0.25:
        _write_skipped("Champion not eligible for live")
        return

    # 4. Get Data
    # For live signal, we usually focus on NIFTY
    symbol = "NIFTY"
    df = get_data(symbol, lookback_days=300, force_refresh=True)

    if df.empty:
        _write_skipped("No Data")
        return

    # 5. Run Logic
    engine = BacktestEngine()
    # We only need signals
    _, _, signal_df = engine.run(df, champion)

    # 6. Determine Signal for TODAY
    # logic: signal at T determines position at T+1 Open.
    # We want position for NOW (Today).
    # So we need signal from Yesterday.

    last_dt = df.index[-1]
    last_is_today = last_dt.date() == now.date()

    if last_is_today:
        # df has today's partial bar.
        # Signal for Today's Open came from Yesterday's Close.
        # Yesterday is index -2.
        if len(signal_df) < 2:
            _write_skipped("Not enough data")
            return
        sig_val = signal_df.iloc[-2]
    else:
        # df ends yesterday.
        # Signal for Today's Open came from Yesterday's Close.
        # Yesterday is index -1.
        sig_val = signal_df.iloc[-1]

    # sig_val is the generated signal (-1, 0, 1)
    # But wait, BacktestEngine returns a Series, but `run` returns `trades, equity, raw_signal`.
    # `raw_signal` is a Series.

    # NOTE: BacktestEngine logic returns -1, 0, 1.
    # But for "Live", we might be holding a position.
    # The simple "Signal" artifact requested is just direction.

    signal_value = int(sig_val) if not pd.isna(sig_val) else 0

    output = {
        "timestamp_ist": now.isoformat(),
        "champion_id": champion.id,
        "instrument": symbol,
        "signal": signal_value,
        "rule_summary": champion.summary,
        "risk": champion.source_code.get("risk", {}),
        "status": "OK",
        "reason": "Market Open, Champion Active"
    }

    with open(LIVE_SIGNAL_FILE, "w") as f:
        json.dump(output, f, indent=2)
    logger.info("Published live signal", signal=signal_value)

def _write_skipped(reason):
    output = {
        "timestamp_ist": datetime.now(pytz.timezone("Asia/Kolkata")).isoformat(),
        "status": "SKIPPED",
        "reason": reason
    }
    with open(LIVE_SIGNAL_FILE, "w") as f:
        json.dump(output, f, indent=2)
    logger.info("Skipped live signal", reason=reason)

if __name__ == "__main__":
    publish_signal()
