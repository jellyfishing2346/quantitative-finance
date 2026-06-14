from dataclasses import dataclass
from datetime import date

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
    # you'll add more metrics in Phase 4 (Sharpe, drawdown etc.)
    def __post_init__(self):
        self.total_return_pct = (self.final_value - self.initial_cash) / self.initial_cash * 100
