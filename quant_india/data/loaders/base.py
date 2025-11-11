from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Iterable, Optional

import pandas as pd


class BaseIngestionJob(ABC):
    """
    Abstract ingestion job that downloads data and returns a dataframe.
    """

    source: str

    def __init__(self, source: str):
        self.source = source

    @abstractmethod
    def fetch(
        self,
        symbols: Iterable[str],
        start: datetime,
        end: datetime,
        interval: str = "1m",
        **kwargs,
    ) -> pd.DataFrame:
        """
        Return a dataframe containing the requested data.
        Implementations must include columns: timestamp, symbol, and raw fields.
        """

    @abstractmethod
    def write(self, df: pd.DataFrame) -> None:
        """
        Persist dataframe to storage in Parquet format with columnar partitions.
        """

    def run(
        self,
        symbols: Iterable[str],
        start: datetime,
        end: datetime,
        interval: str = "1m",
        **kwargs,
    ) -> pd.DataFrame:
        df = self.fetch(symbols=symbols, start=start, end=end, interval=interval, **kwargs)
        if df.empty:
            return df
        df = self._sanitize(df)
        self.write(df)
        return df

    def _sanitize(self, df: pd.DataFrame) -> pd.DataFrame:
        required_cols = {"timestamp", "symbol"}
        missing = required_cols - set(df.columns)
        if missing:
            raise ValueError(f"Missing columns {missing} in dataframe for source {self.source}")
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        return df.sort_values(["symbol", "timestamp"])


class BackfillMixin:
    """
    Mixin that adds backfill capability for missing ranges.
    """

    def backfill(
        self,
        symbols: Iterable[str],
        start: datetime,
        end: datetime,
        interval: str = "1m",
        chunk_days: int = 5,
        **kwargs,
    ) -> pd.DataFrame:
        frames = []
        current_start = pd.Timestamp(start)
        end_ts = pd.Timestamp(end)
        while current_start < end_ts:
            current_end = min(current_start + pd.Timedelta(days=chunk_days), end_ts)
            frames.append(
                self.run(
                    symbols=symbols,
                    start=current_start.to_pydatetime(),
                    end=current_end.to_pydatetime(),
                    interval=interval,
                    **kwargs,
                )
            )
            current_start = current_end
        if not frames:
            return pd.DataFrame()
        return pd.concat(frames, ignore_index=True)
