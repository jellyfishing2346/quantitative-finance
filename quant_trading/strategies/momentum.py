import backtrader as bt
from .base import BaseStrategy

class DualMAMomentum(BaseStrategy):
    params = (
        ("fast_period", 20),
        ("slow_period", 50),
    )

    def __init__(self):
        super().__init__()
        fast = bt.ind.SMA(period=self.params.fast_period)
        slow = bt.ind.SMA(period=self.params.slow_period)
        self.crossover = bt.ind.CrossOver(fast, slow)

    def next(self):
        if self.crossover[0] > 0 and not self.position:
            self.buy(size=self._get_size(self.data.close[0]))
        elif self.crossover[0] < 0 and self.position:
            self.close()
