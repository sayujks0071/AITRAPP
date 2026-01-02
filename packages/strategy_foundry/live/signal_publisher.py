"""
Live Signal Publisher.
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from packages.strategy_foundry.adapters.core_market_hours import MarketHoursAdapter

logger = logging.getLogger(__name__)

class SignalPublisher:
    def __init__(self, results_dir: Path):
        self.results_dir = results_dir
        self.market = MarketHoursAdapter()

    def publish(self, champion, signal: int, instrument: str, metrics: dict):
        """
        Publish signal if market is open and safe.
        """
        out_file = self.results_dir / "live_signal.json"

        status = "OK"
        reason = ""

        # 1. Market Hours Check
        if not self.market.is_market_open():
            status = "SKIPPED"
            reason = "Market closed"

        # 2. Champion Validity Check (re-verify basic gates)
        # Assuming champion passed gates before calling publish, but double check
        if metrics.get("max_dd", 1.0) > 0.25:
            status = "SKIPPED"
            reason = "Champion MaxDD too high"

        # Construct payload
        payload = {
            "timestamp_ist": datetime.now().isoformat(),
            "champion_id": champion.id,
            "instrument": instrument,
            "signal": signal,
            "rule_summary": str(champion.entry_rules) + " / " + str(champion.exit_rules),
            "risk": {
                "stop_loss_atr": champion.params.get("stop_loss_atr"),
                "max_hold": champion.params.get("max_bars_hold")
            },
            "status": status,
            "reason": reason
        }

        with open(out_file, "w") as f:
            json.dump(payload, f, indent=2)

        logger.info(f"Published signal: {status} {reason}")
