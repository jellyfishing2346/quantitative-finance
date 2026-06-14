import backtrader as bt
from .base import BaseStrategy

class BollingerMeanReversion(BaseStrategy):
    params = (
        ("period", 20),
        ("dev_factor", 2.0),
    )

    def __init__(self):
        super().__init__()
        bb = bt.ind.BollingerBands(period=self.params.period, devfactor=self.params.dev_factor)
        self.z = (self.data.close - bb.mid) / (bb.top - bb.mid)

    def next(self):
        if self.z[0] < -1.0 and not self.position:
            self.buy(size=self._get_size(self.data.close[0]))
        elif self.z[0] > 0.0 and self.position:
            self.close()
