# Architecture

## Overview

The framework is organised into five independent layers that compose vertically. Each layer has a single responsibility and communicates with adjacent layers through well-defined interfaces. No layer imports from a layer above it.

```
Dashboard  →  Analytics  →  Backtest Engine  →  Strategies  →  Data Layer
```

This means you can use any layer in isolation — run a backtest without the dashboard, compute metrics without Backtrader, or fetch and cache data without running any strategy.

---

## Layer Responsibilities

### Data Layer (`quant_trading/data/`)

Responsible for acquiring, validating, and persisting OHLCV price data. Nothing above this layer touches a network or a file.

- `fetcher.py` — `DataFetcher` orchestrates data acquisition. It checks the cache first, then tries yfinance, then falls back to Alpha Vantage. All sources are normalised to the same column schema before being returned.
- `cache.py` — `PriceCache` is a SQLite-backed store. Each entry is keyed by a SHA-256 hash of `(symbol, start, end, interval)`. Payloads are pickled DataFrames compressed with zlib at level 6. Entries carry an `expires_at` timestamp; stale entries are evicted on read.
- `models.py` — Pydantic models (`OHLCVBar`, `PriceHistory`) validate every price record at the boundary. Non-positive prices, negative volume, and high < low are all rejected at construction time.

### Strategy Layer (`quant_trading/strategies/`)

Responsible for expressing trading logic as Backtrader `Strategy` subclasses. No I/O, no data fetching.

- `base.py` — `BaseStrategy` provides shared behaviour: fixed-fractional position sizing (`_get_size`), order fill/rejection logging via `notify_order`.
- `momentum.py` — `DualMAMomentum` uses `bt.ind.CrossOver` on two SMAs. Buys when the fast line crosses above the slow line; closes when it crosses below.
- `mean_reversion.py` — `BollingerMeanReversion` computes a Z-score relative to Bollinger Bands. Buys when Z < −1 (oversold); closes when Z > 0 (reverted).
- `signals.py` — Pure pandas implementations of the same signal logic, without any Backtrader dependency. These exist for fast unit testing of signal correctness.

### Backtest Engine (`quant_trading/backtest/`)

Responsible for simulation, parameter search, and result packaging. Wraps Backtrader's cerebro in a clean Python interface.

- `runner.py` — `BacktestRunner` configures cerebro (commission, slippage, analyzers), runs it, and returns a `BacktestResult`. It extracts the equity curve via `TimeReturn` analyzer and the trade count via `TradeAnalyzer`.
- `splitter.py` — `walk_forward_splits` generates `Split(train, test, fold)` objects by sliding a fixed-size window through the DataFrame. The step size is one test window.
- `optimizer.py` — `grid_search` runs every combination in a `param_grid` on the train window and returns results sorted by a configurable metric. `walk_forward_optimize` composes splits + grid search: pick best params on train, evaluate once on test.
- `results.py` — `BacktestResult` is a dataclass that holds the outcome of one run. `__post_init__` computes `total_return_pct` automatically. `compute_metrics()` lazily invokes the analytics layer.

### Analytics Layer (`quant_trading/analytics/`)

Responsible for computing performance metrics from an equity curve. All functions are stateless and take a `pd.Series` of returns.

- `equity.py` — Converts Backtrader's `TimeReturn` dict into a `DataFrame` with `equity` and `returns` columns.
- `metrics.py` — Pure numerical functions: `annualised_return`, `annualised_volatility`, `sharpe_ratio`, `sortino_ratio`, `max_drawdown`, `win_rate`, `profit_factor`.
- `tearsheet.py` — Thin wrapper around QuantStats that generates an HTML tearsheet from a returns series.

### Dashboard (`quant_trading/dashboard/`)

Responsible for rendering the UI and wiring user inputs to the pipeline. Built with Plotly Dash.

- `layout.py` — Defines the page structure as a Python component tree. Sidebar holds all controls; main panel holds charts and the metrics table.
- `callbacks.py` — Contains one main callback triggered by the Run button. It reads all sidebar state, executes the full pipeline (fetch → backtest → metrics), and returns three updated figures.
- `app.py` — Creates the Dash application instance, attaches layout and callbacks, and exposes `main()` for the entry point.

---

## Data Flow

```
User clicks "Run Backtest"
        │
        ▼
callbacks.run_backtest()
        │
        ├─► DataFetcher.fetch(ticker, start, end)
        │       ├─► PriceCache.get()          ← cache hit: return immediately
        │       ├─► yfinance.Ticker.history() ← cache miss: fetch live
        │       ├─► AlphaVantage (fallback)
        │       └─► PriceCache.put()          ← store result
        │
        ├─► BacktestRunner.run(strategy_cls, df, params)
        │       ├─► bt.Cerebro setup (commission, slippage)
        │       ├─► bt.Cerebro.run()
        │       │       └─► Strategy.next() × N bars
        │       ├─► TimeReturn.get_analysis()  → equity curve
        │       └─► BacktestResult(...)
        │
        ├─► BacktestResult.compute_metrics()
        │       └─► metrics.sharpe_ratio(), max_drawdown(), ...
        │
        └─► build_price_chart(), build_equity_chart(), build_metrics_table()
                └─► Plotly figures returned to Dash outputs
```

---

## Key Design Decisions

**Cache-first fetching.** The `DataFetcher` always checks the SQLite cache before making a network request. This makes repeated runs (e.g., tuning parameters on the same dataset) near-instant and means the framework works offline after the first fetch.

**Signals separated from strategy classes.** `signals.py` contains pure pandas implementations of the same logic in the Backtrader strategies. This is intentional — Backtrader strategies are difficult to unit test in isolation, but the signal logic is easy to verify with synthetic data.

**`BacktestResult` as the central artefact.** Everything downstream of a backtest run flows through `BacktestResult`. The dashboard, the optimizer, and any future reporting layer all read from this one object. Adding a new metric means adding it to `compute_metrics()` — nothing else changes.

**Walk-forward over in-sample optimisation.** Parameter optimisation is always performed on a training window, with a single evaluation on a held-out test window. This prevents the most common form of strategy overfitting (selecting parameters that work well on the same data used to evaluate them).
