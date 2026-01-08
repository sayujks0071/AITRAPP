from typing import List, Dict
import json
from pathlib import Path
from .grammar import Strategy, SimpleTrendStrategy, MeanReversionStrategy

class CandidateRegistry:
    @staticmethod
    def save_candidates(strategies: List[Strategy], filepath: Path):
        data = []
        for s in strategies:
            data.append({
                "id": s.get_id(),
                "params": s.params,
                "rule_summary": s.rule_summary
            })

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

    @staticmethod
    def load_candidates(filepath: Path) -> List[Strategy]:
        with open(filepath, 'r') as f:
            data = json.load(f)

        strategies = []
        for item in data:
            params = item['params']
            stype = params.get('type')
            if stype == "SimpleTrend":
                strategies.append(SimpleTrendStrategy(params))
            elif stype == "MeanReversion":
                strategies.append(MeanReversionStrategy(params))
        return strategies
