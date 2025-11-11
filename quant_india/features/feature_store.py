from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Optional

import pandas as pd

from quant_india.common import get_settings
from quant_india.common.io import write_parquet, read_parquet, ensure_parquet_dir


class FeatureStore:
    def __init__(self, root: Optional[Path] = None):
        settings = get_settings()
        self.root = root or settings.feature_store.local_cache
        ensure_parquet_dir(self.root)

    def _path_for(self, feature_name: str, symbol: str, date: str) -> Path:
        return self.root / feature_name / f"date={date}" / f"symbol={symbol}" / "data.parquet"

    def write(self, feature_name: str, symbol: str, df: pd.DataFrame) -> Path:
        if "timestamp" not in df.columns:
            raise ValueError("Feature dataframe must include timestamp column")
        df = df.copy()
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        df = df.sort_values("timestamp")
        grouped = df.groupby(df["timestamp"].dt.tz_convert("Asia/Kolkata").dt.strftime("%Y-%m-%d"))
        written_paths: List[Path] = []
        for date_str, group in grouped:
            path = self._path_for(feature_name, symbol, date_str)
            write_parquet(group, path)
            written_paths.append(path)
        return written_paths[-1] if written_paths else self._path_for(feature_name, symbol, "unknown")

    def load(
        self,
        feature_names: Iterable[str],
        symbols: Iterable[str],
        start: pd.Timestamp,
        end: pd.Timestamp,
    ) -> pd.DataFrame:
        frames = []
        for feature in feature_names:
            for symbol in symbols:
                path = self.root / feature
                if not path.exists():
                    continue
                df = read_parquet(path)
                df = df[(df["symbol"] == symbol) & (df["timestamp"] >= start) & (df["timestamp"] <= end)]
                if df.empty:
                    continue
                cols = [col for col in df.columns if col not in {"symbol", "timestamp"}]
                renamed = {col: f"{feature}__{col}" for col in cols}
                df = df.rename(columns=renamed)
                frames.append(df)
        if not frames:
            return pd.DataFrame()
        merged = frames[0]
        for frame in frames[1:]:
            merged = pd.merge_asof(
                merged.sort_values("timestamp"),
                frame.sort_values("timestamp"),
                on="timestamp",
                by="symbol",
                direction="backward",
            )
        return merged
