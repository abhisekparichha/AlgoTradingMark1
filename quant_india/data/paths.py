from __future__ import annotations

from pathlib import Path
from typing import Tuple

from quant_india.common import get_settings


def raw_path(source: str, date: str, symbol: str) -> Path:
    settings = get_settings()
    return (
        settings.storage.raw_root
        / f"source={source}"
        / f"date={date}"
        / f"symbol={symbol}"
        / "data.parquet"
    )


def processed_path(symbol: str, interval: str, date: str) -> Path:
    settings = get_settings()
    return (
        settings.storage.processed_root
        / f"symbol={symbol}"
        / f"interval={interval}"
        / f"date={date}"
        / "data.parquet"
    )
