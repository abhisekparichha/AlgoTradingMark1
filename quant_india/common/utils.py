from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable

import numpy as np
import pandas as pd


def chunked(iterable: Iterable[Any], chunk_size: int) -> Iterable[list[Any]]:
    chunk: list[Any] = []
    for item in iterable:
        chunk.append(item)
        if len(chunk) >= chunk_size:
            yield chunk
            chunk = []
    if chunk:
        yield chunk


def to_ist_index(df: pd.DataFrame, timestamp_col: str = "timestamp") -> pd.DataFrame:
    if timestamp_col not in df.columns:
        raise ValueError(f"{timestamp_col} missing from dataframe")
    df = df.copy()
    df[timestamp_col] = pd.to_datetime(df[timestamp_col], utc=True).dt.tz_convert("Asia/Kolkata")
    return df.set_index(timestamp_col).sort_index()


def dump_json(data: Dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=_json_serializer)


def _json_serializer(obj: Any) -> Any:
    if isinstance(obj, (np.integer, np.floating)):
        return obj.item()
    if isinstance(obj, (pd.Timestamp, np.datetime64)):
        return pd.Timestamp(obj).isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
