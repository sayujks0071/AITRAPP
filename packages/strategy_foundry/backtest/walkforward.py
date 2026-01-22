import pandas as pd
import numpy as np
from typing import List, Tuple

class WalkForward:
    """
    Manages data splitting for Walk-Forward Analysis.
    """

    @staticmethod
    def split(data: pd.DataFrame, folds: int = 4) -> List[Tuple[pd.DataFrame, pd.DataFrame]]:
        """
        Split data into (Train, Test) tuples.

        Method: Anchored Walk Forward or Rolling?
        Let's use Rolling Window to ensure relevance.
        But for limited data (60 days), Anchored might be better to keep training size.

        Scheme:
        Total = 100%
        Fold Size = 100% / (folds + 1)  (simple approximation)

        Train: [0 : 1*Size] -> Test: [1*Size : 2*Size]
        Train: [0 : 2*Size] -> Test: [2*Size : 3*Size] ... (Anchored)
        """
        if data.empty:
            return []

        n = len(data)
        fold_size = n // (folds + 1)

        splits = []
        for i in range(1, folds + 1):
            train_end = i * fold_size
            test_end = (i + 1) * fold_size

            # Train on accumulated history (Anchored)
            train_data = data.iloc[:train_end]
            # Test on next chunk
            test_data = data.iloc[train_end:test_end]

            splits.append((train_data, test_data))

        return splits
