import pandas as pd
import plotly.graph_objects as go
import pytest
from dash import html

from quant_trading.dashboard.callbacks import (
    build_price_chart,
    build_equity_chart,
    build_metrics_table,
    _build_params,
)


def make_price_df():
    dates = pd.date_range("2023-01-01", periods=10, freq="B")
    return pd.DataFrame({
        "open":  [100.0] * 10,
        "high":  [102.0] * 10,
        "low":   [98.0]  * 10,
        "close": [101.0] * 10,
        "volume": [1_000_000.0] * 10,
    }, index=dates)


def make_equity_df():
    dates = pd.date_range("2023-01-01", periods=10, freq="B")
    return pd.DataFrame({
        "equity":  [100_000, 101_000, 99_000, 102_000, 103_000,
                    101_500, 104_000, 105_000, 103_500, 106_000],
        "returns": [0.0, 0.01, -0.02, 0.03, 0.01,
                    -0.015, 0.025, 0.01, -0.014, 0.024],
    }, index=dates)


def test_build_price_chart_is_figure():
    fig = build_price_chart(make_price_df())
    assert isinstance(fig, go.Figure)

def test_build_price_chart_has_candlestick():
    fig = build_price_chart(make_price_df())
    assert any(isinstance(t, go.Candlestick) for t in fig.data)

def test_build_equity_chart_is_figure():
    fig = build_equity_chart(make_equity_df())
    assert isinstance(fig, go.Figure)

def test_build_equity_chart_has_one_trace():
    fig = build_equity_chart(make_equity_df())
    assert len(fig.data) == 1

def test_build_metrics_table_is_table():
    table = build_metrics_table({"sharpe": 1.2, "max_drawdown": -0.15})
    assert isinstance(table, html.Table)

def test_build_metrics_table_row_count():
    metrics = {"sharpe": 1.2, "sortino": 0.9, "max_drawdown": -0.15}
    table = build_metrics_table(metrics)
    rows = table.children[1].children   # Tbody → rows
    assert len(rows) == 3

def test_params_momentum():
    p = _build_params("DualMAMomentum", fast=10, slow=40)
    assert p == {"fast_period": 10, "slow_period": 40}

def test_params_bollinger():
    p = _build_params("BollingerMeanReversion", fast=20, slow=50)
    assert p == {"period": 20, "dev_factor": 2.0}
