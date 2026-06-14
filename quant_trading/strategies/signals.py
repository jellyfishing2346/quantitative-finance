import pandas as pd

def dual_ma_signal(df, fast, slow):
    fast_ma = df["close"].rolling(fast).mean()
    slow_ma = df["close"].rolling(slow).mean()
    signal = pd.Series(0, index=df.index)
    signal[fast_ma > slow_ma] = 1
    signal[fast_ma < slow_ma] = -1
    return signal

def bollinger_zscore(df, period, dev):
    mid = df["close"].rolling(period).mean()
    std = df["close"].rolling(period).std()
    return (df["close"] - mid) / std
