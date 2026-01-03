import json
from pathlib import Path
from datetime import datetime
import structlog
from packages.strategy_foundry.configs.instrument_map import map_instrument

logger = structlog.get_logger(__name__)

class SignalPublisher:
    def __init__(self, results_dir: Path):
        self.results_dir = results_dir

    def publish(self, champion, signal: int, reason: str = ""):
        """
        Publish signal JSON.
        """
        now = datetime.now()

        # Check eligibility (basic)
        # Should be checked by caller, but we enforce formatting here.

        if signal == 0:
            status = "SKIPPED"
            reason = reason or "Flat/No Signal"
        else:
            status = "OK"

        data = {
            "timestamp_ist": str(now),
            "champion_id": champion['candidate'].id,
            "timeframe": champion['candidate'].timeframe,
            "instrument": champion['candidate'].instrument,
            "proxy_symbol_paper": map_instrument(champion['candidate'].instrument, "paper_proxy"),
            "proxy_symbol_live": map_instrument(champion['candidate'].instrument, "live_proxy"),
            "signal": signal,
            "rule_summary": str(champion['candidate'].entry_rules),
            "risk": {"stop": "ATR", "flat_by": "15:25"},
            "status": status,
            "reason": reason
        }

        outfile = self.results_dir / "live_signal.json"
        with open(outfile, 'w') as f:
            json.dump(data, f, indent=2)

        logger.info(f"Published signal: {status} {signal}")
