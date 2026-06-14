from dash import Input, Output, State, callback, html
import plotly.graph_objects as go
import pandas as pd

from quant_trading.data.fetcher import DataFetcher
from quant_trading.backtest.runner import BacktestRunner
from quant_trading.strategies import DualMAMomentum, BollingerMeanReversion

STRATEGY_MAP = {
    "DualMAMomentum": DualMAMomentum,
    "BollingerMeanReversion": BollingerMeanReversion,
}


def _build_params(strategy_name: str, fast: int, slow: int) -> dict:
    if strategy_name == "BollingerMeanReversion":
        return {"period": fast, "dev_factor": 2.0}
    return {"fast_period": fast, "slow_period": slow}


def build_price_chart(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df["open"], high=df["high"],
        low=df["low"], close=df["close"],
        name="Price",
    ))
    fig.update_layout(
        title="Price",
        xaxis_rangeslider_visible=False,
        margin=dict(l=40, r=20, t=40, b=20),
    )
    return fig


def build_equity_chart(equity_curve: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=equity_curve.index,
        y=equity_curve["equity"],
        mode="lines",
        name="Portfolio Value",
        line=dict(color="#2196F3"),
    ))
    fig.update_layout(
        title="Equity Curve",
        yaxis_title="Portfolio Value ($)",
        margin=dict(l=40, r=20, t=40, b=20),
    )
    return fig


def build_metrics_table(metrics: dict) -> html.Table:
    header = html.Tr([html.Th("Metric"), html.Th("Value")])
    rows = [
        html.Tr([html.Td(k.replace("_", " ").title()), html.Td(f"{v:.4f}")])
        for k, v in metrics.items()
    ]
    return html.Table(
        [html.Thead(header), html.Tbody(rows)],
        style={"width": "100%", "borderCollapse": "collapse", "marginTop": "10px"},
    )


@callback(
    Output("price-chart", "figure"),
    Output("equity-chart", "figure"),
    Output("metrics-table", "children"),
    Output("status-msg", "children"),
    Input("run-btn", "n_clicks"),
    State("ticker", "value"),
    State("start-date", "date"),
    State("end-date", "date"),
    State("strategy", "value"),
    State("fast-period", "value"),
    State("slow-period", "value"),
    prevent_initial_call=True,
)
def run_backtest(n_clicks, ticker, start, end, strategy_name, fast, slow):
    empty = go.Figure()
    try:
        fetcher = DataFetcher()
        history = fetcher.fetch(ticker, start, end)
        df = history.to_dataframe()

        strategy_cls = STRATEGY_MAP[strategy_name]
        params = _build_params(strategy_name, fast, slow)
        result = BacktestRunner().run(strategy_cls, df, params=params)

        price_fig  = build_price_chart(df)
        equity_fig = build_equity_chart(result.equity_curve)
        metrics    = build_metrics_table(result.compute_metrics())
        status     = f"Done — {result.num_trades} trades | return: {result.total_return_pct:.2f}%"

        return price_fig, equity_fig, metrics, status

    except Exception as exc:
        return empty, empty, html.Div(), f"Error: {exc}"
