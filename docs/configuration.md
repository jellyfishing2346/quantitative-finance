# Configuration

All configuration is managed through environment variables, loaded from a `.env` file in the project root via `pydantic-settings`. Settings are validated at startup — missing required values or wrong types raise an error immediately.

---

## Setup

Copy the example file and edit it:

```bash
cp .env.example .env
```

Then edit `.env` with your values. The file is gitignored and will never be committed.

---

## Environment Variables

### `ALPHA_VANTAGE_API_KEY`

**Type:** `str`  
**Default:** `""` (empty — Alpha Vantage disabled)  
**Required:** No

Your Alpha Vantage API key. When empty, Alpha Vantage is never contacted. When set, it is used as a fallback if `yfinance` returns empty data.

Free tier allows 25 requests/day and 5 requests/minute. Premium tiers offer higher limits and more intraday history.

Get a free key at [alphavantage.co](https://www.alphavantage.co/support/#api-key).

```env
ALPHA_VANTAGE_API_KEY=ABC123XYZ
```

---

### `CACHE_DB_PATH`

**Type:** `Path`  
**Default:** `data/cache.db`  
**Required:** No

Path to the SQLite cache database, relative to the project root. The parent directory is created automatically if it doesn't exist.

```env
CACHE_DB_PATH=data/cache.db
```

To use an in-memory database (no persistence, useful for testing):
```env
CACHE_DB_PATH=:memory:
```

---

### `CACHE_TTL_HOURS`

**Type:** `int`  
**Default:** `24`  
**Required:** No

How long a cached price series is considered fresh, in hours. After this period, the next `fetch()` call will re-fetch from the live source and update the cache.

```env
CACHE_TTL_HOURS=24
```

**Guidance by interval:**

| Interval | Recommended TTL |
|----------|----------------|
| `1d` (daily) | 24h — refresh once per trading day |
| `1h` (hourly) | 4h — data changes frequently |
| `1wk`, `1mo` | 168h (1 week) — data rarely changes |

---

### `LOG_LEVEL`

**Type:** `str`  
**Default:** `INFO`  
**Required:** No

Python logging level. Controls the verbosity of output in the terminal.

```env
LOG_LEVEL=INFO
```

| Level | Output |
|-------|--------|
| `DEBUG` | Every cache hit/miss, every order fill, full stack traces |
| `INFO` | Cache hits, backtest completion, trade counts |
| `WARNING` | Fallbacks to Alpha Vantage, order rejections |
| `ERROR` | Unrecovered errors only |

---

## Accessing Settings in Code

```python
from config.settings import settings

print(settings.alpha_vantage_api_key)   # ""
print(settings.cache_db_url)            # "data/cache.db"
print(settings.cache_ttl_hours)         # 24
print(settings.log_level)               # "INFO"
```

The `settings` object is a singleton — it is instantiated once at import time and shared across the application.

---

## Full `.env` Example

```env
# Optional — enables Alpha Vantage as a fallback data source
ALPHA_VANTAGE_API_KEY=your_key_here

# SQLite cache location (relative to project root)
CACHE_DB_PATH=data/cache.db

# Cache TTL in hours
CACHE_TTL_HOURS=24

# Logging verbosity
LOG_LEVEL=INFO
```
