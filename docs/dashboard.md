# Dashboard

The dashboard is a Plotly Dash web application that provides an interactive interface to the entire framework. Enter a ticker and parameters, click Run, and see price history, equity curve, and performance metrics update live.

---

## Starting the Dashboard

```bash
# from the project root, with the virtual environment active
python -m quant_trading.dashboard
```

Then open [http://localhost:8050](http://localhost:8050) in your browser.

The server runs in debug mode by default (`debug=True`), which enables hot-reloading — changes to `layout.py` or `callbacks.py` are reflected on the next page refresh without restarting.

---

## Interface

### Sidebar (left panel)

| Control | Description |
|---------|-------------|
| **Ticker** | Any ticker supported by Yahoo Finance (e.g. `AAPL`, `TSLA`, `SPY`, `BTC-USD`) |
| **Start Date** | Backtest start — pick from the date picker |
| **End Date** | Backtest end |
| **Strategy** | Choose between `DualMAMomentum` and `BollingerMeanReversion` |
| **Fast Period** | Slider: 5–50. Controls fast SMA period (Momentum) or Bollinger period (Mean-Reversion) |
| **Slow Period** | Slider: 20–200. Controls slow SMA period (Momentum only) |
| **Run Backtest** | Executes the full pipeline and updates all panels |

The status bar below the button shows trade count and total return after each run.

### Main Panel (right)

| Panel | Description |
|-------|-------------|
| **Price Chart** | OHLC candlestick chart for the selected ticker and date range. Zoom and pan with Plotly's built-in toolbar. |
| **Equity Curve** | Portfolio value over time. Starts at `$100,000` and reflects every trade, commission, and slippage event. |
| **Metrics Table** | Annualised return, annualised volatility, Sharpe ratio, Sortino ratio, and max drawdown. |

---

## How it Works

When you click **Run Backtest**, Dash calls `callbacks.run_backtest()` with the current values of all sidebar controls. The callback:

1. Calls `DataFetcher.fetch()` — returns instantly if data is cached, otherwise fetches from Yahoo Finance
2. Calls `BacktestRunner.run()` — simulates the strategy with realistic costs
3. Calls `result.compute_metrics()` — computes Sharpe, Sortino, etc.
4. Builds three Plotly figures and returns them to the browser

The browser does not reload — Dash updates only the output components via WebSocket.

### Caching behaviour

The first request for a ticker fetches live data from Yahoo Finance and stores it in SQLite. All subsequent requests for the same ticker and date range are served from cache — typically under 100ms. This makes parameter tuning fast: you can slide the Fast/Slow Period sliders and rerun without refetching data.

To force a fresh fetch (e.g. to get today's data), set `force_refresh=True` in the `DataFetcher.fetch()` call inside `callbacks.py`.

---

## Parameter Guide

### DualMAMomentum

| Control | Maps to | Typical range |
|---------|---------|--------------|
| Fast Period | `fast_period` | 10–30 |
| Slow Period | `slow_period` | 40–100 |

**Tip:** Larger spreads between fast and slow (e.g. 10/100) produce fewer, longer trades. Tighter spreads (e.g. 20/40) produce more trades with more whipsawing in choppy markets.

### BollingerMeanReversion

| Control | Maps to | Typical range |
|---------|---------|--------------|
| Fast Period | `period` | 10–30 |
| Slow Period | *(ignored)* | — |

The `dev_factor` is fixed at `2.0` (standard Bollinger Band width). A future version will expose this as a dedicated slider.

---

## Troubleshooting

**"Error: All data sources failed"**
Yahoo Finance is rate-limited or the ticker is invalid. Wait 30 seconds and retry, or check the ticker symbol.

**Charts are empty after clicking Run**
Check the terminal output for error messages. Common causes: date range too short for the strategy's minimum bars, or network timeout on first fetch.

**Dashboard doesn't load**
Ensure the virtual environment is active and Dash is installed:
```bash
.venv311/bin/pip install dash
python -m quant_trading.dashboard
```

**Slow first run**
Expected — Yahoo Finance data is being fetched and compressed into SQLite. Subsequent runs for the same ticker are fast.
