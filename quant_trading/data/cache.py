import hashlib
import logging
import pickle
import sqlite3
import zlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS price_cache (
    cache_key   TEXT PRIMARY KEY,
    symbol      TEXT NOT NULL,
    interval    TEXT NOT NULL,
    start_date  TEXT NOT NULL,
    end_date    TEXT NOT NULL,
    source      TEXT NOT NULL,
    fetched_at  TEXT NOT NULL,
    expires_at  TEXT NOT NULL,
    payload     BLOB NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_symbol ON price_cache (symbol, interval);
"""


def _make_key(symbol: str, start: str, end: str, interval: str) -> str:
    raw = f"{symbol.upper()}|{start}|{end}|{interval}"
    return hashlib.sha256(raw.encode()).hexdigest()


class PriceCache:
    def __init__(self, db_path: str | Path, ttl_hours: int = 24):
        self._db_path = str(db_path)
        self._ttl = timedelta(hours=ttl_hours)
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, symbol: str, start: str, end: str, interval: str) -> Optional[pd.DataFrame]:
        key = _make_key(symbol, start, end, interval)
        with self._connect() as conn:
            row = conn.execute(
                "SELECT payload, expires_at FROM price_cache WHERE cache_key = ?", (key,)
            ).fetchone()

        if row is None:
            return None

        payload_blob, expires_at_str = row
        if datetime.utcnow() > datetime.fromisoformat(expires_at_str):
            logger.debug("Cache expired for %s %s", symbol, interval)
            self.evict(symbol, start, end, interval)
            return None

        df: pd.DataFrame = pickle.loads(zlib.decompress(payload_blob))
        logger.info("Cache hit: %s [%s → %s] %s", symbol, start, end, interval)
        return df

    def put(
        self,
        symbol: str,
        start: str,
        end: str,
        interval: str,
        df: pd.DataFrame,
        source: str = "unknown",
    ) -> None:
        key = _make_key(symbol, start, end, interval)
        now = datetime.utcnow()
        expires_at = now + self._ttl
        payload_blob = zlib.compress(pickle.dumps(df), level=6)

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO price_cache
                    (cache_key, symbol, interval, start_date, end_date, source, fetched_at, expires_at, payload)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(cache_key) DO UPDATE SET
                    fetched_at = excluded.fetched_at,
                    expires_at = excluded.expires_at,
                    payload    = excluded.payload,
                    source     = excluded.source
                """,
                (key, symbol.upper(), interval, start, end, source, now.isoformat(), expires_at.isoformat(), payload_blob),
            )
        logger.info("Cached %s [%s → %s] %s (%d rows)", symbol, start, end, interval, len(df))

    def evict(self, symbol: str, start: str, end: str, interval: str) -> None:
        key = _make_key(symbol, start, end, interval)
        with self._connect() as conn:
            conn.execute("DELETE FROM price_cache WHERE cache_key = ?", (key,))

    def purge_expired(self) -> int:
        now = datetime.utcnow().isoformat()
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM price_cache WHERE expires_at < ?", (now,))
            return cursor.rowcount

    def clear(self) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM price_cache")

    def stats(self) -> dict:
        with self._connect() as conn:
            total = conn.execute("SELECT COUNT(*) FROM price_cache").fetchone()[0]
            now = datetime.utcnow().isoformat()
            expired = conn.execute(
                "SELECT COUNT(*) FROM price_cache WHERE expires_at < ?", (now,)
            ).fetchone()[0]
        return {"total_entries": total, "expired_entries": expired, "live_entries": total - expired}
