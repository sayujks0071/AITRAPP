"""Strategy grammar and components"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
import hashlib
import json
import random

@dataclass
class StrategyBlock:
    name: str
    params: Dict[str, Any]

    def to_dict(self):
        return {"name": self.name, "params": self.params}

@dataclass
class StrategyCandidate:
    entry_block: StrategyBlock
    exit_blocks: List[StrategyBlock]
    filter_blocks: List[StrategyBlock]
    timeframe: str

    def get_id(self) -> str:
        """Stable hash based on content"""
        # Sort exit and filter blocks to ensure stability regardless of order
        # (though order might matter for execution, for ID generation let's keep it stable based on content)
        # Actually, let's strictly serialize as is.

        data = {
            "entry": self.entry_block.to_dict(),
            "exits": [b.to_dict() for b in self.exit_blocks],
            "filters": [b.to_dict() for b in self.filter_blocks],
            "timeframe": self.timeframe
        }
        s = json.dumps(data, sort_keys=True)
        return hashlib.sha256(s.encode()).hexdigest()[:12]

    def to_dict(self):
        return {
            "id": self.get_id(),
            "entry": self.entry_block.to_dict(),
            "exits": [b.to_dict() for b in self.exit_blocks],
            "filters": [b.to_dict() for b in self.filter_blocks],
            "timeframe": self.timeframe
        }

    @classmethod
    def from_dict(cls, data: Dict):
        entry = StrategyBlock(**data["entry"])
        exits = [StrategyBlock(**b) for b in data["exits"]]
        filters = [StrategyBlock(**b) for b in data["filters"]]
        return cls(entry_block=entry, exit_blocks=exits, filter_blocks=filters, timeframe=data["timeframe"])

    def describe(self) -> str:
        parts = [f"TF: {self.timeframe}"]
        parts.append(f"Entry: {self.entry_block.name} {self.entry_block.params}")
        if self.filter_blocks:
            parts.append("Filters: " + ", ".join([f"{f.name}" for f in self.filter_blocks]))
        parts.append("Exits: " + ", ".join([f"{e.name}" for e in self.exit_blocks]))
        return " | ".join(parts)
