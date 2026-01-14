import pandas as pd
from typing import List

def get_folds(df: pd.DataFrame, n_folds: int = 4) -> List[pd.DataFrame]:
    """
    Split DataFrame into n_folds sequential chunks.
    Used for stability testing (k-fold cross validation on time series).
    """
    if df.empty:
        return []

    n = len(df)
    if n_folds <= 1 or n < n_folds * 100:
        return [df]

    fold_size = n // n_folds
    folds = []
    for i in range(n_folds):
        start = i * fold_size
        end = (i + 1) * fold_size if i < n_folds - 1 else n
        folds.append(df.iloc[start:end].copy())

    return folds
