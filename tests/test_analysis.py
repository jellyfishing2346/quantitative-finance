import pandas as pd
import numpy as np
import pytest
from quant_trading.analytics.metrics import sharpe_ratio, max_drawdown, win_rate, profit_factor
from quant_trading.backtest import BacktestRunner
from quant_trading.strategies import DualMAMomentum

# test metrics on known returns
def test_sharpe_positive_drift():
    returns = pd.Series([0.001] * 252)   # constant 0.1% daily gain
    assert sharpe_ratio(returns) > 0

def test_max_drawdown_negative():
    returns = pd.Series([-0.01] * 50)    # 50 days of losses
    assert max_drawdown(returns) < 0

def test_win_rate():
    pnls = [100, -50, 200, -30, 150]
    assert win_rate(pnls) == pytest.approx(0.6)

def test_profit_factor():
    pnls = [100, -50]
    assert profit_factor(pnls) == pytest.approx(2.0)

# integration: runner produces equity curve
def test_runner_produces_equity_curve():
    runner = BacktestRunner()
    result = runner.run(DualMAMomentum, make_ohlcv_df(200))
    assert result.equity_curve is not None
    assert "returns" in result.equity_curve.columns
    assert "equity" in result.equity_curve.columns

def make_ohlcv_df(n=200):
    rng = np.random.default_rng(42)
    dates = pd.date_range("2023-01-01", periods=n, freq="B")
    close = 100 * np.cumprod(1 + rng.normal(0.0005, 0.01, n))
    spread = rng.uniform(0.002, 0.01, n)
    return pd.DataFrame({
        "open": close * (1 - spread / 2),
        "high": close * (1 + spread),
        "low":  close * (1 - spread),
        "close": close,
        "volume": rng.integers(1_000_000, 10_000_000, n).astype(float),
    }, index=pd.DatetimeIndex(dates, name="Date"))

# integration: metrics compute without error
def test_compute_metrics_keys():
    runner = BacktestRunner()
    result = runner.run(DualMAMomentum, make_ohlcv_df(200))
    m = result.compute_metrics()
    assert set(m.keys()) == {"annualised_return", "annualised_vol", "sharpe", "sortino", "max_drawdown"}
