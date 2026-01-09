import json
import os
from datetime import datetime
import structlog
from packages.strategy_foundry.factory.grammar import StrategyCandidate
from packages.strategy_foundry.factory.generator import GeneratedStrategy
from packages.strategy_foundry.data.loader import DataLoader
from packages.strategy_foundry.adapters.core_market_hours import FoundryMarketHours

logger = structlog.get_logger(__name__)

SIGNAL_FILE = "packages/strategy_foundry/results/live_signal.json"

def publish_signal(champion: StrategyCandidate, symbol: str = "NIFTY"):
    """
    Generate and publish live signal JSON.
    """
    os.makedirs(os.path.dirname(SIGNAL_FILE), exist_ok=True)

    mh = FoundryMarketHours()
    timestamp = datetime.now()

    # 1. Market Hours Check
    if not mh.is_market_open(timestamp):
        _write_signal({
            "timestamp_ist": str(timestamp),
            "status": "SKIPPED",
            "reason": "Market Closed"
        })
        return

    # 2. Load Data (Latest)
    loader = DataLoader()
    try:
        # Force refresh for live signal
        df = loader.load_data(symbol, force_refresh=True)
    except Exception as e:
        _write_signal({
            "timestamp_ist": str(timestamp),
            "status": "SKIPPED",
            "reason": f"Data Load Error: {str(e)}"
        })
        return

    # 3. Generate Signal
    try:
        strategy = GeneratedStrategy(champion)
        # We need to run on full history to get correct indicators
        # Positions are shifted by 1 in backtest (Open of next day).
        # For LIVE signal (intraday or end of day):
        # If we run on data including TODAY'S CLOSE (or current candle),
        # generate_positions() returns target position for TOMORROW OPEN (if Daily).

        # HOWEVER, if we are running HOURLY, and using Daily bars:
        # We only have data up to YESTERDAY close (usually).
        # Yahoo data might have today's live bar.

        # Assumption: We use Daily bars.
        # If today is trading, we might have partial bar.
        # If partial bar is reliable, we use it to predict signal for NOW.

        positions = strategy.generate_positions(df)

        # Latest target position
        last_signal = int(positions.iloc[-1])

        _write_signal({
            "timestamp_ist": str(timestamp),
            "champion_id": champion.id,
            "instrument": symbol,
            "signal": last_signal,
            "rule_summary": champion.rule_summary,
            "risk": {
                "stop_type": champion.grammar.get("stop_type"),
                "params": champion.params
            },
            "status": "OK",
            "reason": "Signal Generated"
        })

    except Exception as e:
        logger.error("Signal generation failed", error=str(e))
        _write_signal({
            "timestamp_ist": str(timestamp),
            "status": "SKIPPED",
            "reason": f"Strategy Error: {str(e)}"
        })

def _write_signal(data: dict):
    with open(SIGNAL_FILE, "w") as f:
        json.dump(data, f, indent=2)
    logger.info("Signal published", status=data["status"])
