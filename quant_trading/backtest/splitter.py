from dataclasses import dataclass
import pandas as pd

@dataclass
class Split:
    train: pd.DataFrame
    test: pd.DataFrame
    fold: int

def walk_forward_splits(
    df: pd.DataFrame,
    train_bars: int,
    test_bars: int,
) -> list[Split]:
    splits = []
    start = 0
    fold = 0
    while start + train_bars + test_bars <= len(df):
        train = df.iloc[start : start + train_bars]
        test  = df.iloc[start + train_bars : start + train_bars + test_bars]
        splits.append(Split(train=train, test=test, fold=fold))
        start += test_bars   # step forward by one test window
        fold += 1
    return splits
