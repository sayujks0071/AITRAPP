from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import hashlib
import json

@dataclass
class StrategyCandidate:
    id: str
    source_code: Dict[str, Any]  # The JSON representation of rules
    created_at: float

    def to_dict(self):
        return {
            "id": self.id,
            "source_code": self.source_code,
            "created_at": self.created_at
        }

    @property
    def summary(self) -> str:
        # Generate human readable summary
        logic = self.source_code.get("logic", [])
        risk = self.source_code.get("risk", {})

        logic_str = " AND ".join([f"{l['type']}({l.get('params', {})})" for l in logic])
        return f"Logic: {logic_str} | Risk: {risk}"

def hash_strategy(source_code: Dict[str, Any]) -> str:
    """Stable hash of the strategy structure"""
    s = json.dumps(source_code, sort_keys=True)
    return hashlib.md5(s.encode()).hexdigest()
