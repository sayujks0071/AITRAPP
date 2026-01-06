from typing import Dict, Any

class StrategyRanker:
    def __init__(self):
        pass

    def score(self, metrics: Dict[str, float]) -> float:
        """
        Composite Score:
        + 30% Sharpe
        + 25% Calmar
        + 20% CAGR
        + 15% Stability
        - 10% Turnover (implied by trades count penalty?)
        """
        # Normalize/Clip for robust scoring
        sharpe = max(min(metrics.get('sharpe', 0), 3.0), -1.0)
        calmar = max(min(metrics.get('calmar', 0), 5.0), 0)
        cagr = max(min(metrics.get('cagr', 0), 1.0), -0.5)
        stability = max(min(metrics.get('stability', 0), 10.0), 0)

        # Penalize low trades (overfitting risk or luck)
        trades = metrics.get('trades', 0)
        trade_penalty = 1.0 if trades > 30 else (trades / 30.0)

        raw_score = (
            0.30 * sharpe +
            0.25 * calmar +
            0.20 * cagr +
            0.15 * stability
        )

        return raw_score * trade_penalty
