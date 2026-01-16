"""Signal Publisher"""
import json
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

RESULTS_DIR = Path(__file__).parent.parent / "results"
SIGNAL_FILE = RESULTS_DIR / "live_signal.json"

class SignalPublisher:
    def __init__(self):
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    def publish(self,
                signal: int,
                instrument: str,
                champion: Dict[str, Any],
                status: str = "OK",
                reason: str = ""):

        output = {
            "timestamp_ist": datetime.now().isoformat(),
            "champion_id": champion.get('id'),
            "instrument": instrument,
            "signal": int(signal),
            "rule_summary": champion.get('rules', {}).get('entry', 'Unknown'),
            "risk": {
                "stop_loss_atr": champion.get('rules', {}).get('stop', 'Unknown')
            },
            "status": status,
            "reason": reason
        }

        with open(SIGNAL_FILE, 'w') as f:
            json.dump(output, f, indent=2)

    def publish_skipped(self, reason: str):
        output = {
            "timestamp_ist": datetime.now().isoformat(),
            "status": "SKIPPED",
            "reason": reason
        }
        with open(SIGNAL_FILE, 'w') as f:
            json.dump(output, f, indent=2)
