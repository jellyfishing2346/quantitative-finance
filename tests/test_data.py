import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from quant_trading.data.cache import PriceCache
from quant_trading.data.models import OHLCVBar, PriceHistory
from quant_trading.data.fetcher import DataFetcher


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_ohlcv_df(n: int = 100, start: str = "2023-01-01") -> pd.DataFrame:
    dates = pd.date_range(start=start, periods=n, freq="B")
    rng = np.random.default_rng(42)
    close = 100.0 * np.cumprod(1 + rng.normal(0.0005, 0.01, n))
    spread = rng.uniform(0.002, 0.01, n)
    df = pd.DataFrame(
        {
            "open": close * (1 - spread / 2),
            "high": close * (1 + spread),
            "low": close * (1 - spread),
            "close": close,
            "volume": rng.integers(1_000_000, 10_000_000, n).astype(float),
            "adjusted_close": close,
        },
        index=pd.DatetimeIndex(dates, name="timestamp"),
    )
    return df


@pytest.fixture
def tmp_db(tmp_path: Path) -> str:
    return str(tmp_path / "test_cache.db")


@pytest.fixture
def cache(tmp_db: str) -> PriceCache:
    return PriceCache(db_path=tmp_db, ttl_hours=1)


@pytest.fixture
def sample_df() -> pd.DataFrame:
    return make_ohlcv_df()


# ---------------------------------------------------------------------------
# OHLCVBar
# ---------------------------------------------------------------------------

class TestOHLCVBar:
    def test_valid_bar(self):
        bar = OHLCVBar(
            timestamp=datetime(2023, 1, 3),
            open=100.0, high=105.0, low=99.0, close=103.0, volume=5_000_000.0,
        )
        assert bar.close == 103.0

    def test_high_less_than_low_raises(self):
        with pytest.raises(Exception):
            OHLCVBar(
                timestamp=datetime(2023, 1, 3),
                open=100.0, high=95.0, low=99.0, close=100.0, volume=1.0,
            )

    def test_non_positive_price_raises(self):
        with pytest.raises(Exception):
            OHLCVBar(
                timestamp=datetime(2023, 1, 3),
                open=0.0, high=1.0, low=0.0, close=0.5, volume=1.0,
            )

    def test_negative_volume_raises(self):
        with pytest.raises(Exception):
            OHLCVBar(
                timestamp=datetime(2023, 1, 3),
                open=100.0, high=101.0, low=99.0, close=100.0, volume=-1.0,
            )


# ---------------------------------------------------------------------------
# PriceHistory
# ---------------------------------------------------------------------------

class TestPriceHistory:
    def test_from_dataframe_roundtrip(self, sample_df: pd.DataFrame):
        ph = PriceHistory.from_dataframe(sample_df, "AAPL", "1d", "test")
        assert ph.symbol == "AAPL"
        assert ph.interval == "1d"
        assert len(ph.bars) == len(sample_df)

    def test_to_dataframe_preserves_shape(self, sample_df: pd.DataFrame):
        ph = PriceHistory.from_dataframe(sample_df, "AAPL", "1d", "test")
        out = ph.to_dataframe()
        assert out.shape[0] == sample_df.shape[0]
        assert set(["open", "high", "low", "close", "volume"]).issubset(out.columns)

    def test_to_dataframe_sorted(self, sample_df: pd.DataFrame):
        ph = PriceHistory.from_dataframe(sample_df, "AAPL", "1d", "test")
        out = ph.to_dataframe()
        assert out.index.is_monotonic_increasing

    def test_empty_bars(self):
        ph = PriceHistory(
            symbol="X", interval="1d", start=date(2023, 1, 1), end=date(2023, 1, 1),
            source="test", fetched_at=datetime.utcnow(), bars=[],
        )
        df = ph.to_dataframe()
        assert df.empty


# ---------------------------------------------------------------------------
# PriceCache
# ---------------------------------------------------------------------------

class TestPriceCache:
    def test_miss_returns_none(self, cache: PriceCache):
        assert cache.get("AAPL", "2023-01-01", "2023-12-31", "1d") is None

    def test_put_then_get(self, cache: PriceCache, sample_df: pd.DataFrame):
        cache.put("AAPL", "2023-01-01", "2023-12-31", "1d", sample_df, source="test")
        result = cache.get("AAPL", "2023-01-01", "2023-12-31", "1d")
        assert result is not None
        pd.testing.assert_frame_equal(result, sample_df)

    def test_put_overwrites(self, cache: PriceCache, sample_df: pd.DataFrame):
        cache.put("AAPL", "2023-01-01", "2023-12-31", "1d", sample_df, source="v1")
        sample_df2 = sample_df.copy()
        sample_df2["close"] = sample_df2["close"] * 2
        cache.put("AAPL", "2023-01-01", "2023-12-31", "1d", sample_df2, source="v2")
        result = cache.get("AAPL", "2023-01-01", "2023-12-31", "1d")
        pd.testing.assert_frame_equal(result, sample_df2)

    def test_evict(self, cache: PriceCache, sample_df: pd.DataFrame):
        cache.put("AAPL", "2023-01-01", "2023-12-31", "1d", sample_df)
        cache.evict("AAPL", "2023-01-01", "2023-12-31", "1d")
        assert cache.get("AAPL", "2023-01-01", "2023-12-31", "1d") is None

    def test_ttl_expiry(self, tmp_db: str, sample_df: pd.DataFrame):
        cache = PriceCache(db_path=tmp_db, ttl_hours=0)
        cache.put("AAPL", "2023-01-01", "2023-12-31", "1d", sample_df)
        assert cache.get("AAPL", "2023-01-01", "2023-12-31", "1d") is None

    def test_stats(self, cache: PriceCache, sample_df: pd.DataFrame):
        cache.put("AAPL", "2023-01-01", "2023-12-31", "1d", sample_df)
        cache.put("MSFT", "2023-01-01", "2023-12-31", "1d", sample_df)
        s = cache.stats()
        assert s["total_entries"] == 2
        assert s["live_entries"] == 2

    def test_purge_expired(self, tmp_db: str, sample_df: pd.DataFrame):
        cache = PriceCache(db_path=tmp_db, ttl_hours=0)
        cache.put("AAPL", "2023-01-01", "2023-12-31", "1d", sample_df)
        removed = cache.purge_expired()
        assert removed == 1

    def test_clear(self, cache: PriceCache, sample_df: pd.DataFrame):
        cache.put("AAPL", "2023-01-01", "2023-12-31", "1d", sample_df)
        cache.clear()
        assert cache.stats()["total_entries"] == 0

    def test_key_isolation(self, cache: PriceCache, sample_df: pd.DataFrame):
        cache.put("AAPL", "2023-01-01", "2023-12-31", "1d", sample_df)
        assert cache.get("MSFT", "2023-01-01", "2023-12-31", "1d") is None
        assert cache.get("AAPL", "2022-01-01", "2022-12-31", "1d") is None
        assert cache.get("AAPL", "2023-01-01", "2023-12-31", "1h") is None


# ---------------------------------------------------------------------------
# DataFetcher
# ---------------------------------------------------------------------------

class TestDataFetcher:
    def _make_fetcher(self, tmp_db: str) -> DataFetcher:
        return DataFetcher(cache=PriceCache(db_path=tmp_db, ttl_hours=1))

    def test_cache_hit_no_network(self, tmp_db: str, sample_df: pd.DataFrame):
        cache = PriceCache(db_path=tmp_db, ttl_hours=1)
        cache.put("AAPL", "2023-01-01", "2023-12-31", "1d", sample_df, source="test")
        fetcher = DataFetcher(cache=cache)
        ph = fetcher.fetch("AAPL", "2023-01-01", "2023-12-31", "1d")
        assert ph.symbol == "AAPL"
        assert len(ph.bars) == len(sample_df)

    @patch("quant_trading.data.fetcher.DataFetcher._fetch_yfinance")
    def test_yfinance_success(self, mock_yf, tmp_db: str, sample_df: pd.DataFrame):
        mock_yf.return_value = sample_df
        fetcher = self._make_fetcher(tmp_db)
        ph = fetcher.fetch("AAPL", "2023-01-01", "2023-12-31", "1d")
        assert ph.source == "yfinance"
        assert len(ph.bars) == len(sample_df)

    @patch("quant_trading.data.fetcher.DataFetcher._fetch_yfinance")
    @patch("quant_trading.data.fetcher.DataFetcher._fetch_alpha_vantage")
    @patch("quant_trading.data.fetcher.settings")
    def test_yfinance_fallback_to_av(self, mock_settings, mock_av, mock_yf, tmp_db: str, sample_df: pd.DataFrame):
        mock_settings.alpha_vantage_api_key = "fake_key"
        mock_settings.cache_db_url = tmp_db
        mock_settings.cache_ttl_hours = 1
        mock_yf.side_effect = RuntimeError("network down")
        mock_av.return_value = sample_df
        fetcher = self._make_fetcher(tmp_db)
        ph = fetcher.fetch("AAPL", "2023-01-01", "2023-12-31", "1d")
        assert ph.source == "alpha_vantage"

    @patch("quant_trading.data.fetcher.DataFetcher._fetch_yfinance")
    def test_all_sources_fail_raises(self, mock_yf, tmp_db: str):
        mock_yf.side_effect = RuntimeError("network down")
        fetcher = self._make_fetcher(tmp_db)
        with pytest.raises(RuntimeError, match="All data sources failed"):
            fetcher.fetch("AAPL", "2023-01-01", "2023-12-31", "1d")

    @patch("quant_trading.data.fetcher.DataFetcher._fetch_yfinance")
    def test_fetch_multiple(self, mock_yf, tmp_db: str, sample_df: pd.DataFrame):
        mock_yf.return_value = sample_df
        fetcher = self._make_fetcher(tmp_db)
        results = fetcher.fetch_multiple(["AAPL", "MSFT"], "2023-01-01", "2023-12-31")
        assert set(results.keys()) == {"AAPL", "MSFT"}

    @patch("quant_trading.data.fetcher.DataFetcher._fetch_yfinance")
    def test_fetch_multiple_partial_failure(self, mock_yf, tmp_db: str, sample_df: pd.DataFrame):
        def side_effect(symbol, *args, **kwargs):
            if symbol == "BAD":
                raise RuntimeError("bad ticker")
            return sample_df

        mock_yf.side_effect = side_effect
        fetcher = self._make_fetcher(tmp_db)
        results = fetcher.fetch_multiple(["AAPL", "BAD"], "2023-01-01", "2023-12-31")
        assert "AAPL" in results
        assert "BAD" not in results

    def test_validate_missing_columns(self, tmp_db: str):
        bad_df = pd.DataFrame({"open": [1.0], "close": [1.0]})
        fetcher = self._make_fetcher(tmp_db)
        with pytest.raises(ValueError, match="Missing columns"):
            fetcher._validate_dataframe(bad_df, "TEST")

    def test_validate_non_positive_price(self, tmp_db: str, sample_df: pd.DataFrame):
        bad = sample_df.copy()
        bad.iloc[0, bad.columns.get_loc("close")] = 0.0
        fetcher = self._make_fetcher(tmp_db)
        with pytest.raises(ValueError, match="Non-positive"):
            fetcher._validate_dataframe(bad, "TEST")

    def test_validate_high_less_than_low(self, tmp_db: str, sample_df: pd.DataFrame):
        bad = sample_df.copy()
        idx = bad.columns.get_loc
        bad.iloc[0, idx("high")] = 1.0
        bad.iloc[0, idx("low")] = 999.0
        fetcher = self._make_fetcher(tmp_db)
        with pytest.raises(ValueError, match="high < low"):
            fetcher._validate_dataframe(bad, "TEST")
