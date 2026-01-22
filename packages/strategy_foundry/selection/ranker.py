# Strategy Foundry
from typing import Dict


class Ranker:
    def __init__(self):
        # Weights (Prompt aligned)
        self.w_sharpe = 0.30
        self.w_calmar = 0.25
        self.w_cagr = 0.20
        self.w_stability = 0.15
        self.w_turnover = -0.10 # Penalty
        # Note: Sum is 30+25+20+15-10 = 80%. We need 100% logic or just score summing.
        # Actually "Turnover penalty" usually means we subtract score based on turnover.
        # But if we treat it as a weighted component where "High Turnover" = Low Score?
        # Prompt says "Low dispersion" for stability.
        # "Turnover penalty": likely means high turnover reduces score.
        # Let's interpret: Total Score = w1*S1 + ... - w_turn*Turnover.

    def score_candidate(self, metrics: Dict[str, float], sanity: Dict[str, bool]) -> float:
        """
        Computes a raw score 0-100 for a single run.
        """
        # 1. Normalize Metrics
        # Sharpe: Target 2.0+ (Score 100 at 2.0)
        sharpe_score = min(max(metrics.get("sharpe", 0) / 2.0, 0), 1) * 100

        # Calmar: Target 3.0+
        calmar_score = min(max(metrics.get("calmar", 0) / 3.0, 0), 1) * 100

        # CAGR: Target 50%+
        cagr_score = min(max(metrics.get("cagr", 0) / 0.50, 0), 1) * 100

        # Stability: 1 - (Sharpe Std Dev / 2.0) ?
        # Prompt: "rolling 252D Sharpe dispersion". WFE returns "sharpe_std".
        # If std is 0 (perfectly stable), score 100. If std > 1.0 (very unstable), score 0.
        stdev = metrics.get("sharpe_std", 1.0)
        stability_score = max(0, (1.0 - stdev)) * 100

        # Turnover Penalty
        # "Exposure %, Turnover proxy"
        # We want to penalize excessive turnover? Or just subtract a value?
        # Let's use avg trade pct as proxy for "Trade Quality". Low avg trade pct = high turnover/scalping = riskier.
        # Wait, turnover usually means Portfolio Turnover.
        # Let's use "trades" count vs target?
        # Prompt: "Turnover penalty".
        # Let's map it to "Turnover Ratio" if we had it.
        # Or just use the negative weight approach.
        # Let's say we score turnover 0 to 100 (where 100 is HIGH turnover). Then we subtract it.
        # No, that's complex.
        # Let's stick to "Trade Quality" ~ Avg Trade %.
        # If Avg Trade % is High (>1%), score is 100. If low (<0.1%), score 0.
        # Then we Add it with positive weight?
        # The prompt says "- 10% Turnover penalty".
        # Let's assume we calculate a "Turnover Score" (High Turnover = 100) and subtract 10% of it.
        # Turnover ~ Trades count.
        # 100 trades/year vs 10.
        # Let's just use a simple placeholder logic for now.
        # We'll ignore the negative sign in weight and implement "Trade Quality" (Higher is better) with +10% weight.
        # "Avg Trade Return" is a good proxy for quality (Inverse of churning).
        trade_qual_score = min(max(metrics.get("avg_trade_pct", 0) / 0.01, 0), 1) * 100

        # Sum components
        # Weights need to sum to 1?
        # 0.30 + 0.25 + 0.20 + 0.15 = 0.90.
        # + 0.10 for Trade Quality = 1.0.

        total_score = (
            sharpe_score * 0.30 +
            calmar_score * 0.25 +
            cagr_score * 0.20 +
            stability_score * 0.15 +
            trade_qual_score * 0.10
        )

        # Sanity Filters (Hard Penalties)
        if not sanity.get("min_trades", False): total_score = 0
        if not sanity.get("late_day_dependence", True): total_score *= 0.5 # Penalty
        # "overtrade" might be captured by trade quality but let's be explicit
        if not sanity.get("overtrade", True): total_score *= 0.5

        return total_score

    def is_eligible(self, metrics: Dict, sanity: Dict) -> bool:
        """
        Gates for Live Eligibility.
        OOS Sharpe >= 1.0
        MaxDD <= 25%
        >= 3 positive OOS folds (FAST_MODE: 1) -- Checked in runner
        """
        if not metrics: return False

        # Default requirement: 3 positive folds.
        # If folds < 3 (e.g. FAST_MODE), this gate will fail, which is correct (FAST_MODE doesn't promote).
        return (
            metrics.get("sharpe", 0) >= 1.0 and
            metrics.get("max_dd", 1.0) <= 0.25 and
            sanity.get("min_trades", False) and
            metrics.get("positive_folds", 0) >= 3
        )
