import backtrader as bt
import pandas as pd
from .results import BacktestResult

class BacktestRunner:
    def __init__(
        self,
        commission: float = 0.001,   # 0.1% per trade
        slippage: float = 0.0005,    # 0.05%
        initial_cash: float = 100_000,
    ):
        self.commission = commission
        self.slippage = slippage
        self.initial_cash = initial_cash


    def run(self, strategy_cls, df: pd.DataFrame, params: dict = {}) -> BacktestResult:
        cerebro = bt.Cerebro()
        cerebro.addstrategy(strategy_cls, **params)
        cerebro.adddata(bt.feeds.PandasData(dataname=df))
        cerebro.broker.setcash(self.initial_cash)
        # set commission:
        cerebro.broker.setcommission(commission=self.commission)
        # set slippage — Backtrader uses a "perc" slippage model:
        cerebro.broker.set_slippage_perc(self.slippage)
        # add trade analyzer so you can count trades:
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades")

        results = cerebro.run()
        strat = results[0]

        trade_analysis = strat.analyzers.trades.get_analysis()
        num_trades = trade_analysis.get("total", {}).get("closed", 0)

        return BacktestResult(
            strategy_name=strategy_cls.__name__,
            params=params,
            start=df.index[0].date(),
            end=df.index[-1].date(),
            initial_cash=self.initial_cash,
            final_value=cerebro.broker.getvalue(),
            num_trades=num_trades,
        )
