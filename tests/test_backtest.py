import numpy as np
import pandas as pd
import pytest
from quant_trading.backtest import BacktestRunner, BacktestResult, walk_forward_splits, grid_search
from quant_trading.strategies import DualMAMomentum, BollingerMeanReversion


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
def test_result_total_return_pct():
    r = BacktestResult(
        strategy_name="Test",
        params={},
        start=pd.Timestamp("2023-01-01").date(),
        end=pd.Timestamp("2023-12-31").date(),
        initial_cash=100_000,
        final_value=110_000,
        num_trades=5,
    )
    assert r.total_return_pct == pytest.approx(10.0)
def test_runner_returns_result():
    runner = BacktestRunner()
    df = make_ohlcv_df(200)
    result = runner.run(DualMAMomentum, df)
    assert isinstance(result, BacktestResult)
    assert result.strategy_name == "DualMAMomentum"
    assert result.initial_cash == 100_000
    assert result.final_value > 0
def test_commission_reduces_return():
    df = make_ohlcv_df(200)
    free   = BacktestRunner(commission=0.0, slippage=0.0).run(DualMAMomentum, df)
    costly = BacktestRunner(commission=0.01, slippage=0.0).run(DualMAMomentum, df)
    assert costly.final_value <= free.final_value
def test_splitter_produces_correct_shapes():
    df = make_ohlcv_df(500)
    splits = walk_forward_splits(df, train_bars=300, test_bars=100)
    assert len(splits) == 2
    for s in splits:
        assert len(s.train) == 300
        assert len(s.test) == 100
def test_splitter_no_overlap():
    df = make_ohlcv_df(500)
    splits = walk_forward_splits(df, train_bars=300, test_bars=100)
    for s in splits:
        train_idx = set(s.train.index)
        test_idx  = set(s.test.index)
        assert train_idx.isdisjoint(test_idx)
def test_grid_search_sorted_by_return():
    df = make_ohlcv_df(300)
    runner = BacktestRunner()
    results = grid_search(
        DualMAMomentum, df,
        param_grid={"fast_period": [5, 10], "slow_period": [20, 30]},
        runner=runner,
    )
    assert len(results) == 4
    returns = [r.total_return_pct for r in results]
    assert returns == sorted(returns, reverse=True)
def test_splitter_too_little_data():
    df = make_ohlcv_df(50)
    splits = walk_forward_splits(df, train_bars=300, test_bars=100)
    assert splits == []
