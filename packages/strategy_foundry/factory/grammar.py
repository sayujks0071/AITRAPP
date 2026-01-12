from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import hashlib
import json

@dataclass
class StrategyCandidate:
    id: str
    entry_logic: Dict[str, Any]
    exit_logic: Dict[str, Any]
    params: Dict[str, Any]
    source_grammar: str = "v1"

    def to_json(self) -> str:
        return json.dumps({
            "id": self.id,
            "entry_logic": self.entry_logic,
            "exit_logic": self.exit_logic,
            "params": self.params,
            "source_grammar": self.source_grammar
        }, sort_keys=True)

    @staticmethod
    def from_json(json_str: str) -> 'StrategyCandidate':
        data = json.loads(json_str)
        return StrategyCandidate(
            id=data["id"],
            entry_logic=data["entry_logic"],
            exit_logic=data["exit_logic"],
            params=data["params"],
            source_grammar=data.get("source_grammar", "v1")
        )

    def generate_id(self):
        # Create stable ID from content
        content = json.dumps({
            "entry": self.entry_logic,
            "exit": self.exit_logic,
            "params": self.params
        }, sort_keys=True)
        self.id = hashlib.md5(content.encode()).hexdigest()

class Grammar:
    ENTRY_TYPES = ["trend_following", "breakout", "mean_reversion"]
    EXIT_TYPES = ["fixed_risk", "trailing_stop"]

    # We will define the logic structure here.
    # Actually generator uses this.
