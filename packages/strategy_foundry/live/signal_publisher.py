"""Signal Publisher"""
import os
import json
import logging
from datetime import datetime
import pytz

logger = logging.getLogger(__name__)
IST = pytz.timezone("Asia/Kolkata")
SIGNAL_FILE = "packages/strategy_foundry/results/live_signal.json"

def publish_signal(champion: dict, signal: int, instrument: str, proxy_symbol: str, reason: str = ""):
    """
    Publish live signal JSON.
    """
    os.makedirs(os.path.dirname(SIGNAL_FILE), exist_ok=True)

    payload = {
        "timestamp_ist": datetime.now(IST).isoformat(),
        "champion_id": champion.get("id"),
        "instrument": instrument,
        "proxy_symbol": proxy_symbol,
        "signal": signal, # -1, 0, 1
        "reason": reason,
        "risk": {
            "stop_model": "ATR",
            "params": champion.get("params", {}).get("atr_period", 14)
        }
    }

    with open(SIGNAL_FILE, "w") as f:
        json.dump(payload, f, indent=2)

    logger.info(f"Signal published: {signal} for {instrument}")
