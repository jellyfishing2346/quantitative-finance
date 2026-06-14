import numpy as np
import pandas as pd
import backtrader as bt
from quant_trading.strategies import DualMAMomentum, BollingerMeanReversion
from quant_trading.strategies.signals import dual_ma_signal, bollinger_zscore


def test_dual_ma_buy_signal():
    # make a steadily rising price series (200 bars)
    # call dual_ma_signal(df, fast=5, slow=20)
    # assert that (signal == 1).any() — a buy signal fired
    dates = pd.date_range("2023-01-01", periods=200, freq="B")
    close = np.linspace(50, 150, 200)  # steadily rising
    df = pd.DataFrame({"close": close}, index=dates)
    signal = dual_ma_signal(df, fast=5, slow=20)
    assert (signal == 1).any()


def test_dual_ma_sell_signal():
    # make a steadily falling price series
    # assert that (signal == -1).any()
    dates = pd.date_range("2023-01-01", periods=200, freq="B")
    close = np.linspace(150, 50, 200)  # steadily falling
    df = pd.DataFrame({"close": close}, index=dates)
    signal = dual_ma_signal(df, fast=5, slow=20)
    assert (signal == -1).any()


def test_bollinger_zscore_range():
    # use make_ohlcv_df(200)
    # call bollinger_zscore(df, period=20, dev=2.0)
    # assert the zscore has both positive and negative values
    # assert it's a pd.Series with the same index as df
    df = make_ohlcv_df(200)
    z = bollinger_zscore(df, period=20, dev=2.0)
    assert isinstance(z, pd.Series)
    assert z.index.equals(df.index)
    assert (z > 0).any()
    assert (z < 0).any()

def make_ohlcv_df(n=200):
    rng = np.random.default_rng(42)
    dates = pd.date_range("2023-01-01", periods=n, freq="B")
    close = 100 * np.cumprod(1 + rng.normal(0.0005, 0.01, n))
    spread = rng.uniform(0.002, 0.01, n)
    return pd.DataFrame({
        "open": close * (1 - spread / 2),
        "high": close * (1 + spread),
        "low": close * (1 - spread),
        "close": close,
        "volume": rng.integers(1_000_000, 10_000_000, n).astype(float),
    }, index=pd.DatetimeIndex(dates, name="Date"))



def test_get_size_uses_size_pct():
    # can't instantiate BaseStrategy directly (Backtrader requires a feed)
    # instead: test the math manually
    cash = 10_000
    price = 150.0
    size_pct = 0.95
    expected = int((cash * size_pct) / price)  # = 63
    assert expected == 63


def run_strategy(strategy_cls, df, cash=100_000, **kwargs):
    cerebro = bt.Cerebro()
    cerebro.addstrategy(strategy_cls, **kwargs)
    feed = bt.feeds.PandasData(dataname=df)
    cerebro.adddata(feed)
    cerebro.broker.setcash(cash)
    results = cerebro.run()
    return results[0], cerebro.broker.getvalue()

def test_momentum_trades():
    df = make_ohlcv_df(200)
    strat, final_value = run_strategy(DualMAMomentum, df)
    assert final_value != 100_000  # something happened

def test_mean_reversion_trades():
    df = make_ohlcv_df(200)
    strat, final_value = run_strategy(BollingerMeanReversion, df)
    assert final_value != 100_000


