"""Walk Forward Analysis"""
import pandas as pd
from typing import List, Tuple
from datetime import timedelta

class WalkForward:
    def __init__(self, folds: int = 4, train_ratio: float = 0.7):
        self.folds = folds
        self.train_ratio = train_ratio

    def split(self, df: pd.DataFrame) -> List[Tuple[pd.DataFrame, pd.DataFrame]]:
        """
        Return list of (train, test) splits.
        Using Expanding Window or Rolling?
        Prompt says: "5m: 4 folds".
        Usually WF is: Train (Period 1), Test (Period 2). Train (1+2), Test (3).
        """
        n = len(df)
        if n < 1000:
            return [(df, df)] # Too small, just return full (sanity check)

        # Divide data into N+1 chunks
        # Chunk 0 is initial train
        # Chunks 1..N are test folds

        chunk_size = n // (self.folds + 1)
        splits = []

        for i in range(self.folds):
            # Train on 0..i
            train_end_idx = (i + 1) * chunk_size
            # Test on i+1
            test_end_idx = (i + 2) * chunk_size

            # To avoid huge training sets on intraday (slow), maybe rolling window?
            # "Expanding window" is safer for regime.
            # But let's limit training window if needed.

            train = df.iloc[:train_end_idx]
            test = df.iloc[train_end_idx:test_end_idx]

            splits.append((train, test))

        return splits
