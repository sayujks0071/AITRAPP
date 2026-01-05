"""
Walk Forward Validation
"""
import pandas as pd
from typing import List, Tuple

class WalkForward:
    @staticmethod
    def split(df: pd.DataFrame, folds: int = 4) -> List[Tuple[pd.DataFrame, pd.DataFrame]]:
        """
        Split data into Train/Test folds.
        Expanding window for training, sliding for testing.
        """
        if len(df) < 500: # Not enough data
            return []

        n = len(df)
        fold_size = n // (folds + 1)

        splits = []
        for i in range(1, folds + 1):
            train_end = i * fold_size
            test_end = (i + 1) * fold_size

            # Ensure we don't go out of bounds
            if test_end > n:
                test_end = n

            train_data = df.iloc[:train_end]
            test_data = df.iloc[train_end:test_end]

            splits.append((train_data, test_data))

        return splits
