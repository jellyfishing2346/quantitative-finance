# API Reference

Complete reference for all public classes and functions.

---

## `quant_trading.data`

### `DataFetcher`

```python
DataFetcher(cache: PriceCache = None)
```

| Method | Signature | Returns |
|--------|-----------|---------|
| `fetch` | `(symbol, start, end, interval="1d", force_refresh=False)` | `PriceHistory` |
| `fetch_multiple` | `(symbols, start, end, interval="1d", force_refresh=False)` | `dict[str, PriceHistory]` |

---

### `PriceCache`

```python
PriceCache(db_path: str | Path, ttl_hours: int = 24)
```

| Method | Signature | Returns |
|--------|-----------|---------|
| `get` | `(symbol, start, end, interval)` | `pd.DataFrame \| None` |
| `put` | `(symbol, start, end, interval, df, source="unknown")` | `None` |
| `evict` | `(symbol, start, end, interval)` | `None` |
| `purge_expired` | `()` | `int` (rows removed) |
| `clear` | `()` | `None` |
| `stats` | `()` | `dict` |

---

### `OHLCVBar`

```python
OHLCVBar(
    timestamp: datetime,
    open: float,
    high: float,
    low: float,
    close: float,
    volume: float,
    adjusted_close: float = None,
)
```

Raises `ValidationError` if: `high < low`, any price ≤ 0, or `volume < 0`.

---

### `PriceHistory`

```python
PriceHistory(
    symbol: str,
    interval: str,
    start: date,
    end: date,
    source: str,
    fetched_at: datetime,
    bars: list[OHLCVBar],
)
```

| Method | Signature | Returns |
|--------|-----------|---------|
| `to_dataframe` | `()` | `pd.DataFrame` |
| `from_dataframe` | `(df, symbol, interval, source)` — classmethod | `PriceHistory` |

---

## `quant_trading.strategies`

### `BaseStrategy`

Backtrader strategy base class. Not instantiated directly.

| Member | Type | Description |
|--------|------|-------------|
| `params.size_pct` | `float` | Fraction of cash per trade. Default `0.95`. |
| `params.stop_pct` | `float \| None` | Stop-loss percentage. Default `None`. |
| `_get_size(price)` | method | Returns share count for current cash and price. |
| `notify_order(order)` | method | Logs fills and rejections. |

---

### `DualMAMomentum(BaseStrategy)`

| Param | Type | Default |
|-------|------|---------|
| `fast_period` | `int` | `20` |
| `slow_period` | `int` | `50` |

---

### `BollingerMeanReversion(BaseStrategy)`

| Param | Type | Default |
|-------|------|---------|
| `period` | `int` | `20` |
| `dev_factor` | `float` | `2.0` |

---

### Signal Functions (`quant_trading.strategies.signals`)

```python
dual_ma_signal(df: pd.DataFrame, fast: int, slow: int) -> pd.Series
```
Returns `+1` where fast MA > slow MA, `-1` where fast < slow, `0` otherwise.

```python
bollinger_zscore(df: pd.DataFrame, period: int, dev: float) -> pd.Series
```
Returns Z-score of close relative to Bollinger Band width.

---

## `quant_trading.backtest`

### `BacktestRunner`

```python
BacktestRunner(
    commission: float = 0.001,
    slippage: float = 0.0005,
    initial_cash: float = 100_000,
)
```

| Method | Signature | Returns |
|--------|-----------|---------|
| `run` | `(strategy_cls, df, params={})` | `BacktestResult` |

---

### `BacktestResult`

```python
@dataclass
class BacktestResult:
    strategy_name: str
    params: dict
    start: date
    end: date
    initial_cash: float
    final_value: float
    num_trades: int
    total_return_pct: float       # auto-computed
    equity_curve: pd.DataFrame    # columns: equity, returns
```

| Method | Signature | Returns |
|--------|-----------|---------|
| `compute_metrics` | `()` | `dict[str, float]` |

---

### `walk_forward_splits`

```python
walk_forward_splits(
    df: pd.DataFrame,
    train_bars: int,
    test_bars: int,
) -> list[Split]
```

Returns a list of `Split(train, test, fold)` dataclasses.

---

### `grid_search`

```python
grid_search(
    strategy_cls,
    train_df: pd.DataFrame,
    param_grid: dict,
    runner: BacktestRunner,
    sort_by: str = "total_return_pct",
) -> list[BacktestResult]
```

---

### `walk_forward_optimize`

```python
walk_forward_optimize(
    strategy_cls,
    df: pd.DataFrame,
    param_grid: dict,
    train_bars: int = 750,
    test_bars: int = 250,
    runner: BacktestRunner = None,
) -> list[dict]
```

Each dict in the returned list has keys: `fold`, `best_params`, `train_result`, `test_result`.

---

## `quant_trading.analytics`

### Metric Functions

All accept a `pd.Series` of daily returns. All return `float`.

```python
annualised_return(returns: pd.Series) -> float
annualised_volatility(returns: pd.Series) -> float
sharpe_ratio(returns: pd.Series, risk_free: float = 0.0) -> float
sortino_ratio(returns: pd.Series, risk_free: float = 0.0) -> float
max_drawdown(returns: pd.Series) -> float
```

Trade-level functions accept a `list[float]` of per-trade P&Ls:

```python
win_rate(trade_pnls: list[float]) -> float
profit_factor(trade_pnls: list[float]) -> float
```

### `extract_equity_curve`

```python
extract_equity_curve(
    time_return: dict,
    initial_cash: float,
) -> pd.DataFrame
```

Converts Backtrader's `TimeReturn` analysis dict to a DataFrame with columns `equity` and `returns`.

### `generate_tearsheet`

```python
generate_tearsheet(
    returns: pd.Series,
    output_path: str,
    title: str = "Strategy",
) -> None
```

### `print_stats`

```python
print_stats(returns: pd.Series) -> None
```

---

## `config.settings`

```python
from config.settings import settings

settings.alpha_vantage_api_key   # str
settings.cache_db_url            # str  (resolved path, parent dir created)
settings.cache_ttl_hours         # int
settings.log_level               # str
```
