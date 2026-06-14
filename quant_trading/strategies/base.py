import logging
import backtrader as bt

logger = logging.getLogger(__name__)

class BaseStrategy(bt.Strategy):
    params = (
        ("size_pct", 0.95),
        ("stop_pct", None),
    )

    def notify_order(self, order):
        if order.status in [order.Completed]:
            logger.info("Filled: price=%.2f  size=%d", order.executed.price, order.executed.size)
        elif order.status in [order.Canceled, order.Rejected]:
            logger.warning("Order canceled/rejected: %s", order.getstatusname())

    def _get_size(self, price):
        cash = self.broker.get_cash()
        return int((cash * self.params.size_pct) / price)
