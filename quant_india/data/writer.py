from __future__ import annotations

from pathlib import Path

import pandas as pd

from quant_india.common.io import ensure_parquet_dir, write_parquet


def write_partitioned(df: pd.DataFrame, root: Path, partition_cols: list[str]) -> None:
    if not partition_cols:
        raise ValueError("partition_cols must not be empty")
    ensure_parquet_dir(root)
    write_parquet(df, root / "data.parquet", partition_cols=partition_cols)
