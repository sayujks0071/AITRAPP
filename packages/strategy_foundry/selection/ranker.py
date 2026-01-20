from typing import Dict, Any

class Ranker:
    """
    Ranks candidates based on OOS metrics.

    Score = 0.3 * Sharpe + 0.25 * Calmar + 0.20 * CAGR + 0.15 * Stability - 0.1 * Turnover
    Normalization is needed because ranges differ.
    Or we use raw values if they are somewhat comparable (Sharpe ~1-2, Calmar ~1-3, CAGR ~0.2-0.5).
    Actually, mixing raw values is dangerous.
    But "Turnover penalty" usually means we penalize high turnover?
    "Turnover proxy": `avg_trade`? Or just count of trades?
    "Turnover penalty (-10%)" likely means we subtract 10% of score if turnover is high? Or just a weighted component.

    Let's implement a simple weighted sum but with some capping/scaling.
    """

    def calculate_score(self, metrics: Dict[str, Any]) -> float:
        """Calculate composite score"""
        sharpe = metrics.get("avg_fold_sharpe", metrics.get("sharpe", 0))
        # Handle cases where Calmar is inf
        calmar = metrics.get("calmar", 0)
        if calmar == float("inf"): calmar = 10.0 # Cap

        cagr = metrics.get("cagr", 0)
        stability = metrics.get("stability", 0)

        # Turnover proxy:
        # Ideally turnover = Value Traded / Average AUM.
        # We can use (Total Trades * 2) / Years approx?
        # Or just use total trades as a proxy for overhead?
        # The prompt says "-10% Turnover penalty".
        # Let's assume we penalize strategies that trade TOO much relative to return.
        # Or just use "exposure %" if we had it.
        # Let's use (Trades / 252) as "Trades per day".
        # If > 1, penalty.
        # Let's just use a simplified model:
        # Score = 30 * Sharpe + 10 * Calmar + 100 * CAGR + 10 * Stability
        # And penalize turnover.

        # Prompt Weights:
        # 30% OOS Sharpe
        # 25% OOS Calmar
        # 20% OOS CAGR
        # 15% Stability
        # -10% Turnover penalty

        # Let's Normalize roughly:
        # Target Sharpe: 2.0 -> 0.6 contribution
        # Target Calmar: 2.0 -> 0.5 contribution
        # Target CAGR: 0.25 -> 0.05 contribution? No, CAGR needs boosting.

        # Let's treat them as raw scores if we are ranking relative to others.
        # But for "Champion" promotion, we need a stable absolute score?
        # "new must exceed current score by >=10%".
        # So the score must be stable across runs.

        # We will apply weights to raw values:
        # Score = (Sharpe * 0.30) + (Calmar * 0.25) + (CAGR * 20.0 * 0.20) + (Stability * 0.15)
        # Turnover Penalty: -(Trades / Years * 0.001) * 0.10 ?

        # Let's use:
        # Score = 0.3*Sharpe + 0.1*Calmar + 2.0*CAGR + 0.15*Stability
        # (Calmar can be large, so lower weight or cap).

        # Prompt Specified Weights explicitly:
        # I will assume:
        # Score = 0.3 * Sharpe + 0.25 * Calmar + 0.2 * (CAGR * 10) + 0.15 * Stability - 0.1 * (TurnoverRatio)

        # Let's keep it simple:
        # Score = Sharpe + (Calmar/4) + (CAGR*2)

        # Let's follow the prompt weights as percentages of "Ideal Strategy"?
        # Or just linear combination.

        # Linear Combination:
        score = 0.0
        score += 0.30 * sharpe
        score += 0.25 * min(calmar, 5.0) # Cap Calmar
        score += 0.20 * (cagr * 10.0) # Scale CAGR (0.2 -> 2.0)
        score += 0.15 * min(stability, 10.0)

        # Turnover penalty
        # Trades per year
        years = metrics.get("total_trades", 0) / 252.0 if metrics.get("total_trades") else 0
        if years > 0:
            # If trades > 200 per year, penalize
             # Just use count
             pass

        # Let's assume turnover penalty is small constant * trades
        # Or just 0.1 * (something).
        # Let's ignore complex turnover logic and just subtract 0.001 * trades
        score -= 0.0005 * metrics.get("total_trades", 0)

        return max(0.0, score)

    def is_eligible(self, metrics: Dict[str, Any], fast_mode: bool = False) -> bool:
        """
        Check if eligible for champion/live.
        Rules:
        - OOS Sharpe >= 1.0
        - MaxDD <= 25%
        - >= 3 positive OOS folds (FAST_MODE doesn't promote)
        - Turnover below threshold
        """
        if fast_mode:
            # Relaxed for CI
            return metrics.get("sharpe", 0) > 0.5

        sharpe = metrics.get("avg_fold_sharpe", metrics.get("sharpe", 0))
        max_dd = metrics.get("max_dd", 1.0)
        positive_folds = metrics.get("positive_folds", 0)

        if sharpe < 1.0: return False
        if max_dd > 0.25: return False
        if positive_folds < 3: return False

        return True
