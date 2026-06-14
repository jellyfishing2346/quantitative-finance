import pandas as pd

def extract_equity_curve(time_return: dict, initial_cash: float) -> pd.DataFrame:
    returns = pd.Series(time_return).sort_index()
    returns.index = pd.to_datetime(returns.index)
    equity = initial_cash * (1 + returns).cumprod()
    return pd.DataFrame({"equity": equity, "returns": returns})
