from datetime import date, datetime
from typing import Optional
import pandas as pd
from pydantic import BaseModel, field_validator, model_validator


class OHLCVBar(BaseModel):
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    adjusted_close: Optional[float] = None

    @field_validator("open", "high", "low", "close")
    @classmethod
    def price_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError(f"Price must be positive, got {v}")
        return v

    @field_validator("volume")
    @classmethod
    def volume_non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError(f"Volume must be non-negative, got {v}")
        return v

    @model_validator(mode="after")
    def high_gte_low(self) -> "OHLCVBar":
        if self.high < self.low:
            raise ValueError(f"high ({self.high}) must be >= low ({self.low})")
        return self


class PriceHistory(BaseModel):
    symbol: str
    interval: str
    start: date
    end: date
    source: str
    fetched_at: datetime
    bars: list[OHLCVBar]

    def to_dataframe(self) -> pd.DataFrame:
        if not self.bars:
            return pd.DataFrame(columns=["open", "high", "low", "close", "volume", "adjusted_close"])
        records = [b.model_dump() for b in self.bars]
        df = pd.DataFrame(records)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.set_index("timestamp").sort_index()
        return df

    @classmethod
    def from_dataframe(
        cls,
        df: pd.DataFrame,
        symbol: str,
        interval: str,
        source: str,
    ) -> "PriceHistory":
        df = df.copy()
        if df.index.name == "timestamp" or isinstance(df.index, pd.DatetimeIndex):
            df = df.reset_index().rename(columns={"index": "timestamp", "Date": "timestamp", "Datetime": "timestamp"})

        col_map = {
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume",
            "Adj Close": "adjusted_close",
        }
        df = df.rename(columns=col_map)

        timestamp_col = next((c for c in df.columns if c.lower() in ("timestamp", "date", "datetime")), None)
        if timestamp_col and timestamp_col != "timestamp":
            df = df.rename(columns={timestamp_col: "timestamp"})

        bars = [OHLCVBar(**row) for row in df.to_dict(orient="records")]
        return cls(
            symbol=symbol,
            interval=interval,
            start=bars[0].timestamp.date(),
            end=bars[-1].timestamp.date(),
            source=source,
            fetched_at=datetime.utcnow(),
            bars=bars,
        )
