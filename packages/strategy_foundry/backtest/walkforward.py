import pandas as pd
from typing import List, Tuple

class WalkForward:
    def __init__(self, n_folds=5, train_ratio=0.7):
        self.n_folds = n_folds
        self.train_ratio = train_ratio

    def split(self, df: pd.DataFrame) -> List[Tuple[pd.DataFrame, pd.DataFrame]]:
        """
        Expanding window walk-forward.
        """
        n = len(df)
        min_train = int(n * 0.2)
        fold_size = int((n - min_train) / self.n_folds)

        splits = []
        for i in range(self.n_folds):
            train_end = min_train + i * fold_size
            test_end = train_end + fold_size

            # Or fixed window? Expanding is safer for regime.
            # Train: Start -> train_end
            # Test: train_end -> test_end

            train_df = df.iloc[:train_end]
            test_df = df.iloc[train_end:test_end]

            if len(test_df) > 0:
                splits.append((train_df, test_df))

        return splits
