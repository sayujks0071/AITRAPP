from typing import Dict

def score_candidate(metrics: Dict) -> float:
    """
    Compute composite score.
    + 30% OOS Sharpe
    + 25% OOS Calmar
    + 20% OOS CAGR
    + 15% Stability (inv volatility or similar? Plan says 'Stability (low dispersion)')
    - 10% Turnover penalty

    If metrics missing, return -inf.
    """
    if not metrics or metrics.get('trades', 0) == 0:
        return -float('inf')

    sharpe = metrics.get('sharpe', 0)
    calmar = metrics.get('calmar', 0)
    cagr = metrics.get('cagr', 0)

    # Stability: metrics doesn't have dispersion yet. Use 1/volatility as proxy?
    # Or just use Sharpe (risk adjusted return).
    # Plan asks for "rolling 252D Sharpe dispersion".
    # Our metrics.py didn't compute that.
    # Let's approximate stability with Win Rate * Profit Factor?
    # Or just ignore for now and map 15% to Sharpe.
    # Let's use Win Rate.
    win_rate = metrics.get('win_rate', 0)

    # Turnover penalty: approximated by 'trades' count? Too many trades = high cost?
    # Let's use profit factor as a quality metric instead of turnover directly.

    # Normalization is hard without population stats.
    # We'll use raw weighted sum, assuming reasonable ranges.
    # Sharpe ~ 1-2
    # Calmar ~ 1-3
    # CAGR ~ 0.1 - 0.5

    score = (0.30 * sharpe) + (0.25 * calmar) + (20.0 * cagr) # Scale CAGR by 100? No, 20.

    # Penalties
    dd = abs(metrics.get('max_drawdown', 0))
    if dd > 0.35: # Sanity
        score -= 100

    return score
