import numpy as np
import pandas as pd

TRADING_DAYS = 252

def annualised_return(returns: pd.Series) -> float:
    # compound the daily returns, then annualise
    total = (1 + returns).prod()
    n_years = len(returns) / TRADING_DAYS
    return total ** (1 / n_years) - 1

def annualised_volatility(returns: pd.Series) -> float:
    return returns.std() * np.sqrt(TRADING_DAYS)

def sharpe_ratio(returns: pd.Series, risk_free: float = 0.0) -> float:
    excess = returns - risk_free / TRADING_DAYS
    if excess.std() == 0:
        return 0.0
    return (excess.mean() / excess.std()) * np.sqrt(TRADING_DAYS)

def sortino_ratio(returns: pd.Series, risk_free: float = 0.0) -> float:
    excess = returns - risk_free / TRADING_DAYS
    downside = excess[excess < 0].std()
    if downside == 0:
        return 0.0
    return (excess.mean() / downside) * np.sqrt(TRADING_DAYS)

def max_drawdown(returns: pd.Series) -> float:
    equity = (1 + returns).cumprod()
    peak = equity.cummax()
    drawdown = (equity - peak) / peak
    return drawdown.min()   # negative number, e.g. -0.23 = 23% drawdown

def win_rate(trade_pnls: list) -> float:
    if not trade_pnls:
        return 0.0
    wins = [p for p in trade_pnls if p > 0]
    return len(wins) / len(trade_pnls)

def profit_factor(trade_pnls: list) -> float:
    gross_profit = sum(p for p in trade_pnls if p > 0)
    gross_loss   = abs(sum(p for p in trade_pnls if p < 0))
    if gross_loss == 0:
        return float("inf")
    return gross_profit / gross_loss

