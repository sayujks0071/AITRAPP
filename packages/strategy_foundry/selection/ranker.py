import pandas as pd
from typing import List, Dict, Any

def rank_candidates(results: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Rank candidates based on composite score.
    results: List of dicts containing 'id', 'metrics', 'params'
    """
    if not results:
        return pd.DataFrame()

    df = pd.DataFrame([
        {
            'id': r['id'],
            'sharpe': r['metrics']['sharpe'],
            'calmar': r['metrics']['calmar'],
            'cagr': r['metrics']['cagr'],
            'stability': r['metrics'].get('stability_score', 0),
            'trades': r['metrics']['trades'],
            'max_dd': r['metrics']['max_dd'],
            'win_rate': r['metrics']['win_rate'],
            'metrics': r['metrics'],
            'params': r['params'],
            'rule_summary': r['rule_summary']
        }
        for r in results
    ])

    # Normalize
    # We want relative ranking.
    # Simple MinMax scaling or Rank scaling.
    # Let's use Rank (percentile) to be robust to outliers.

    cols = ['sharpe', 'calmar', 'cagr', 'stability']
    for col in cols:
        df[f'{col}_rank'] = df[col].rank(pct=True)

    # Turnover penalty: More trades = bad? Not necessarily.
    # High turnover = high cost.
    # Let's penalize very high trade count?
    # Or just use raw count rank (inverted).
    df['turnover_rank'] = df['trades'].rank(pct=True, ascending=False)

    # Composite Score
    # 30% Sharpe, 25% Calmar, 20% CAGR, 15% Stability, 10% Turnover
    df['score'] = (
        0.30 * df['sharpe_rank'] +
        0.25 * df['calmar_rank'] +
        0.20 * df['cagr_rank'] +
        0.15 * df['stability_rank'] +
        0.10 * df['turnover_rank']
    )

    df.sort_values('score', ascending=False, inplace=True)
    return df
