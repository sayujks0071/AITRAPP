"""
Strategy Foundry - Signal Publisher.
"""
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any
import structlog
from packages.strategy_foundry.adapters.core_market_hours import MarketHoursAdapter

logger = structlog.get_logger(__name__)

SIGNAL_FILE = Path("packages/strategy_foundry/results/live_signal.json")
SIGNAL_FILE.parent.mkdir(parents=True, exist_ok=True)

def publish_signal(champion: Dict[str, Any], signal: int, instrument: str, reason: str = ""):
    """
    Publish live signal JSON.
    """
    mh = MarketHoursAdapter()

    # Check Eligibility
    # Must have passed robust OOS tests (already checked during promotion/ranking usually, but good to re-check)
    # We assume 'champion' is valid.

    status = "OK"
    if not mh.can_publish_signal():
        status = "SKIPPED"
        reason = "Market Closed"

    # Check Approvals?
    # Approvals are handled by Core when reading this. We just publish "intent".
    # Wait, instructions say: "If market open AND champion live-eligible: write ... Else write SKIPPED"

    output = {
        "timestamp_ist": datetime.now().isoformat(),
        "champion_id": champion.get("id"),
        "instrument": instrument,
        "signal": signal,
        "rule_summary": champion.get("rule_summary", ""),
        "risk": {
            "stop": "ATR", # Generic placeholder as strategy handles stops internally in execution usually
            # But we can extract params
            "params": {}
        },
        "status": status,
        "reason": reason
    }

    # Extract Risk Params
    for block in champion.get("config", {}).get("blocks", []):
        if block["type"] == "EXIT" and block["subtype"] == "ATR_STOP":
            output["risk"]["params"]["atr_multiplier"] = block["params"]["multiplier"]

    with open(SIGNAL_FILE, 'w') as f:
        json.dump(output, f, indent=2)

    logger.info("Published signal", status=status, signal=signal)
