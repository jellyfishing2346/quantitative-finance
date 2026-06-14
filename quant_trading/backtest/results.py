from dataclasses import dataclass, field
from datetime import date
import pandas as pd


@dataclass
class BacktestResult:
    strategy_name: str
    params: dict
    start: date
    end: date
    initial_cash: float
    final_value: float
    num_trades: int
    total_return_pct: float = 0.0
    equity_curve: pd.DataFrame = field(default=None)

    def __post_init__(self):
        self.total_return_pct = (self.final_value - self.initial_cash) / self.initial_cash * 100

    def compute_metrics(self) -> dict:
        if self.equity_curve is None:
            return {}
        from quant_trading.analytics.metrics import (
            annualised_return, annualised_volatility, sharpe_ratio, sortino_ratio, max_drawdown
        )
        r = self.equity_curve["returns"].dropna()
        return {
            "annualised_return": annualised_return(r),
            "annualised_vol":    annualised_volatility(r),
            "sharpe":            sharpe_ratio(r),
            "sortino":           sortino_ratio(r),
            "max_drawdown":      max_drawdown(r),
        }
