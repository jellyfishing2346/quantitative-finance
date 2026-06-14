import logging
import time
from datetime import date, datetime
from typing import Optional

import pandas as pd

from config.settings import settings
from .cache import PriceCache
from .models import PriceHistory

logger = logging.getLogger(__name__)

_YFINANCE_INTERVAL_MAP = {
    "1d": "1d", "1wk": "1wk", "1mo": "1mo",
    "1h": "1h", "30m": "30m", "15m": "15m", "5m": "5m", "1m": "1m",
}

_AV_INTERVAL_MAP = {
    "1d": ("TIME_SERIES_DAILY_ADJUSTED", None),
    "1wk": ("TIME_SERIES_WEEKLY_ADJUSTED", None),
    "1mo": ("TIME_SERIES_MONTHLY_ADJUSTED", None),
    "1h": ("TIME_SERIES_INTRADAY", "60min"),
    "30m": ("TIME_SERIES_INTRADAY", "30min"),
    "15m": ("TIME_SERIES_INTRADAY", "15min"),
    "5m": ("TIME_SERIES_INTRADAY", "5min"),
    "1m": ("TIME_SERIES_INTRADAY", "1min"),
}


class DataFetcher:
    """Fetch OHLCV data with SQLite caching. yfinance is the primary source;
    Alpha Vantage is the fallback when an API key is configured."""

    def __init__(self, cache: Optional[PriceCache] = None):
        self._cache = cache or PriceCache(
            db_path=settings.cache_db_url,
            ttl_hours=settings.cache_ttl_hours,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fetch(
        self,
        symbol: str,
        start: str | date,
        end: str | date,
        interval: str = "1d",
        force_refresh: bool = False,
    ) -> PriceHistory:
        start_str = str(start)
        end_str = str(end)
        symbol = symbol.upper()

        if not force_refresh:
            cached_df = self._cache.get(symbol, start_str, end_str, interval)
            if cached_df is not None:
                return PriceHistory.from_dataframe(cached_df, symbol, interval, source="cache")

        df, source = self._fetch_live(symbol, start_str, end_str, interval)
        self._validate_dataframe(df, symbol)
        self._cache.put(symbol, start_str, end_str, interval, df, source=source)
        return PriceHistory.from_dataframe(df, symbol, interval, source=source)

    def fetch_multiple(
        self,
        symbols: list[str],
        start: str | date,
        end: str | date,
        interval: str = "1d",
        force_refresh: bool = False,
    ) -> dict[str, PriceHistory]:
        results: dict[str, PriceHistory] = {}
        for symbol in symbols:
            try:
                results[symbol] = self.fetch(symbol, start, end, interval, force_refresh)
            except Exception as exc:
                logger.error("Failed to fetch %s: %s", symbol, exc)
        return results

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _fetch_live(self, symbol: str, start: str, end: str, interval: str) -> tuple[pd.DataFrame, str]:
        errors: list[str] = []

        try:
            df = self._fetch_yfinance(symbol, start, end, interval)
            if df is not None and not df.empty:
                return df, "yfinance"
            errors.append("yfinance: returned empty data")
            logger.warning("yfinance returned empty data for %s", symbol)
        except Exception as exc:
            errors.append(f"yfinance: {exc}")
            logger.warning("yfinance error for %s: %s", symbol, exc)

        if settings.alpha_vantage_api_key:
            try:
                df = self._fetch_alpha_vantage(symbol, start, end, interval)
                if df is not None and not df.empty:
                    return df, "alpha_vantage"
                errors.append("alpha_vantage: returned empty data")
            except Exception as exc:
                errors.append(f"alpha_vantage: {exc}")
                logger.warning("Alpha Vantage error for %s: %s", symbol, exc)
        else:
            errors.append("alpha_vantage: no API key configured")

        raise RuntimeError(
            f"All data sources failed for {symbol} [{start} → {end}] {interval}. "
            f"Details: {' | '.join(errors)}"
        )

    def _fetch_yfinance(self, symbol: str, start: str, end: str, interval: str) -> Optional[pd.DataFrame]:
        import yfinance as yf

        yf_interval = _YFINANCE_INTERVAL_MAP.get(interval)
        if yf_interval is None:
            raise ValueError(f"Unsupported interval for yfinance: {interval!r}")

        # yf.download is more stable than Ticker.history across yfinance versions
        df = yf.download(
            symbol, start=start, end=end, interval=yf_interval,
            auto_adjust=False, progress=False, threads=False,
        )

        if df.empty:
            return None

        # yfinance 1.x returns MultiIndex columns even for a single ticker
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df = df.rename(columns={
            "Open": "open", "High": "high", "Low": "low",
            "Close": "close", "Volume": "volume", "Adj Close": "adjusted_close",
        })
        df.index.name = "timestamp"
        keep = [c for c in ("open", "high", "low", "close", "volume", "adjusted_close") if c in df.columns]
        return df[keep]

    def _fetch_alpha_vantage(self, symbol: str, start: str, end: str, interval: str) -> Optional[pd.DataFrame]:
        from alpha_vantage.timeseries import TimeSeries

        function, av_interval = _AV_INTERVAL_MAP.get(interval, (None, None))
        if function is None:
            raise ValueError(f"Unsupported interval for Alpha Vantage: {interval!r}")

        ts = TimeSeries(key=settings.alpha_vantage_api_key, output_format="pandas")

        if av_interval:
            df, _ = ts.get_intraday(symbol=symbol, interval=av_interval, outputsize="full")
        elif function == "TIME_SERIES_DAILY_ADJUSTED":
            df, _ = ts.get_daily_adjusted(symbol=symbol, outputsize="full")
        elif function == "TIME_SERIES_WEEKLY_ADJUSTED":
            df, _ = ts.get_weekly_adjusted(symbol=symbol)
        else:
            df, _ = ts.get_monthly_adjusted(symbol=symbol)

        df.index = pd.to_datetime(df.index)
        df.index.name = "timestamp"
        df = df.rename(columns={
            "1. open": "open", "2. high": "high", "3. low": "low",
            "4. close": "close", "5. adjusted close": "adjusted_close",
            "6. volume": "volume",
        })
        df = df.sort_index()

        start_dt = pd.Timestamp(start)
        end_dt = pd.Timestamp(end)
        df = df.loc[start_dt:end_dt]

        keep = [c for c in ("open", "high", "low", "close", "volume", "adjusted_close") if c in df.columns]
        return df[keep] if not df.empty else None

    @staticmethod
    def _validate_dataframe(df: pd.DataFrame, symbol: str) -> None:
        required = {"open", "high", "low", "close", "volume"}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"Missing columns for {symbol}: {missing}")

        if (df[["open", "high", "low", "close"]] <= 0).any().any():
            raise ValueError(f"Non-positive prices found in {symbol} data")

        if (df["high"] < df["low"]).any():
            raise ValueError(f"high < low found in {symbol} data")
