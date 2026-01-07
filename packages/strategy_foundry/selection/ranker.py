"""
Strategy Ranker
"""
from typing import Dict, Any

class Ranker:
    @staticmethod
    def calculate_score(metrics: Dict[str, float], weights: Dict[str, float]) -> float:
        """
        Calculate weighted score for a strategy based on metrics.
        """
        # Normalize metrics roughly
        # Sharpe: 0 to 3
        # Calmar: 0 to 5
        # CAGR: 0 to 1
        # Stability: (1 - std_dev)
        # Turnover: penalize

        score = 0.0

        # Sharpe (clip at 3)
        sharpe_score = min(max(metrics['sharpe'], 0), 3.0) / 3.0
        score += sharpe_score * weights.get('sharpe', 0.25)

        # Calmar (clip at 5)
        calmar_score = min(max(metrics['calmar'], 0), 5.0) / 5.0
        score += calmar_score * weights.get('calmar', 0.25)

        # CAGR (clip at 100%)
        cagr_score = min(max(metrics['cagr'], 0), 1.0)
        score += cagr_score * weights.get('cagr', 0.20)

        # Stability (Approximated by positive folds ratio)
        # Using metrics['positive_folds'] assuming 4 folds max
        stability_score = metrics.get('positive_folds', 0) / 4.0
        score += stability_score * weights.get('stability', 0.15)

        # Turnover (Lower is better? Or just bonus for low?)
        # Let's say we want efficient trades. Profit Factor is a good proxy.
        pf_score = min(max(metrics['profit_factor'] - 1, 0), 2.0) / 2.0
        score += pf_score * weights.get('turnover', 0.10) # reusing turnover weight for efficiency

        return score * 100.0 # Scale to 0-100
