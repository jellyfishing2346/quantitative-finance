# Data Layer

The data layer is responsible for one thing: giving you a clean, validated `PriceHistory` object for any ticker, date range, and interval — whether or not you have a network connection right now.

---

## Components

### `DataFetcher`

The main entry point. Call `fetch()` and it handles everything else.

```python
from quant_trading.data import DataFetcher

fetcher = DataFetcher()
history = fetcher.fetch("AAPL", start="2022-01-01", end="2023-12-31", interval="1d")
df = history.to_dataframe()
```

**Source priority:**
1. SQLite cache (instant, no network)
2. Yahoo Finance via `yfinance`
3. Alpha Vantage (requires `ALPHA_VANTAGE_API_KEY` in `.env`)

If all sources fail, a `RuntimeError` is raised with a clear message.

#### `fetch()` parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `symbol` | `str` | required | Ticker symbol, e.g. `"AAPL"` |
| `start` | `str \| date` | required | Start date, e.g. `"2022-01-01"` |
| `end` | `str \| date` | required | End date, e.g. `"2023-12-31"` |
| `interval` | `str` | `"1d"` | Bar size — see supported intervals below |
| `force_refresh` | `bool` | `False` | Skip cache and fetch live data |

#### Supported intervals

| Interval | yfinance | Alpha Vantage |
|----------|----------|---------------|
| `1d` | ✅ | ✅ |
| `1wk` | ✅ | ✅ |
| `1mo` | ✅ | ✅ |
| `1h` | ✅ | ✅ |
| `30m` | ✅ | ✅ |
| `15m` | ✅ | ✅ |
| `5m` | ✅ | ✅ |
| `1m` | ✅ | ✅ |

Note: intraday intervals (`1h` and below) have limited history on yfinance (60 days). Alpha Vantage provides up to 2 years of intraday data with a premium key.

#### Fetching multiple tickers

```python
results = fetcher.fetch_multiple(
    ["AAPL", "MSFT", "GOOGL"],
    start="2022-01-01",
    end="2023-12-31",
)
# returns dict[str, PriceHistory]
# symbols that fail are skipped — partial results are returned
```

---

### `PriceCache`

SQLite-backed cache with TTL expiry and zlib compression. You rarely need to interact with this directly — `DataFetcher` manages it automatically — but it's useful for maintenance tasks.

```python
from quant_trading.data import PriceCache

cache = PriceCache(db_path="data/cache.db", ttl_hours=24)

# check what's in the cache
print(cache.stats())
# {'total_entries': 12, 'expired_entries': 0, 'live_entries': 12}

# force-refresh a specific entry
cache.evict("AAPL", "2022-01-01", "2023-12-31", "1d")

# clean up all expired entries
removed = cache.purge_expired()
print(f"Removed {removed} stale entries")

# wipe everything
cache.clear()
```

**Implementation notes:**
- Each entry is keyed by a SHA-256 hash of `(symbol, start, end, interval)` — collisions are impossible in practice.
- DataFrames are serialised with `pickle` and compressed with `zlib` at level 6 before storage. A year of daily OHLCV data compresses to ~15KB.
- The database runs in WAL (Write-Ahead Logging) mode, which allows concurrent reads while a write is in progress.
- TTL is checked on every read. Stale entries are evicted lazily on access, or eagerly via `purge_expired()`.

---

### `OHLCVBar` and `PriceHistory`

Pydantic models that validate every price record at the data boundary.

```python
from quant_trading.data.models import OHLCVBar, PriceHistory
from datetime import datetime

# OHLCVBar validates on construction
bar = OHLCVBar(
    timestamp=datetime(2023, 6, 1),
    open=150.0, high=155.0, low=149.0, close=153.0, volume=50_000_000.0
)

# these all raise ValidationError
OHLCVBar(..., high=100.0, low=110.0)    # high < low
OHLCVBar(..., close=-5.0)               # non-positive price
OHLCVBar(..., volume=-1000.0)           # negative volume
```

`PriceHistory` wraps a list of bars with metadata and provides two conversion methods:

```python
# convert to DataFrame (timestamps as index, sorted ascending)
df = history.to_dataframe()

# construct from a DataFrame
history = PriceHistory.from_dataframe(df, symbol="AAPL", interval="1d", source="yfinance")
```

**Validated constraints:**
- `open`, `high`, `low`, `close` must all be strictly positive
- `high >= low` (enforced after all fields are set via `model_validator`)
- `volume >= 0`

---

## Column Schema

All data sources are normalised to this schema before caching or returning:

| Column | Type | Description |
|--------|------|-------------|
| `open` | `float` | Opening price |
| `high` | `float` | Session high |
| `low` | `float` | Session low |
| `close` | `float` | Closing price (unadjusted) |
| `volume` | `float` | Trade volume |
| `adjusted_close` | `float?` | Dividend/split-adjusted close (when available) |

The DataFrame index is a `DatetimeIndex` named `timestamp`, sorted ascending.

---

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `CACHE_DB_PATH` | `data/cache.db` | SQLite database path |
| `CACHE_TTL_HOURS` | `24` | Hours before a cached entry expires |
| `ALPHA_VANTAGE_API_KEY` | `""` | Required only if yfinance fails |

See [configuration.md](configuration.md) for full details.
