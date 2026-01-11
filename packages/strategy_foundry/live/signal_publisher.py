import json
import structlog
from pathlib import Path
from datetime import datetime
from typing import Any
from packages.strategy_foundry.adapters.core_market_hours import MarketHoursAdapter

logger = structlog.get_logger(__name__)
RESULTS_DIR = Path("packages/strategy_foundry/results")

class SignalPublisher:
    def publish(self, symbol: str, signal: int, strategy: Any, reason: str = "OK", status: str = "OK"):
        market = MarketHoursAdapter()

        # Schema
        output = {
            "timestamp_ist": str(datetime.now(market.get_timezone())),
            "champion_id": strategy.id if strategy else None,
            "instrument": symbol,
            "signal": signal,
            "rule_summary": strategy.rule_summary if strategy else None,
            "risk": strategy.to_dict()["risk"] if strategy else None,
            "status": status,
            "reason": reason
        }

        # Write to file
        path = RESULTS_DIR / "live_signal.json"
        try:
            with open(path, "w") as f:
                json.dump(output, f, indent=2)
            logger.info("Published live signal", file=path, status=status)
        except Exception as e:
            logger.error("Failed to publish signal", error=str(e))
