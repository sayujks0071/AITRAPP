"""
Walk Forward Validation
"""
import pandas as pd
from typing import List, Tuple

class WalkForward:
    @staticmethod
    def split(df: pd.DataFrame, folds: int = 4) -> List[Tuple[pd.DataFrame, pd.DataFrame]]:
        """
        Split data into expanding window train/test splits.
        Returns: List of (train_df, test_df)
        """
        if len(df) < 500: # Min data requirement
            return []

        n_samples = len(df)
        fold_size = n_samples // (folds + 1)

        splits = []
        for i in range(folds):
            # Train: Start to (i+1)*fold_size
            # Test: (i+1)*fold_size to (i+2)*fold_size
            train_end = (i + 1) * fold_size
            test_end = (i + 2) * fold_size

            # Ensure we don't go out of bounds
            if test_end > n_samples:
                test_end = n_samples

            train_df = df.iloc[:train_end]
            test_df = df.iloc[train_end:test_end]

            splits.append((train_df, test_df))

        return splits
