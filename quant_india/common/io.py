from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq


def ensure_parquet_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_parquet(df: pd.DataFrame, path: Path, partition_cols: Optional[Iterable[str]] = None) -> None:
    ensure_parquet_dir(path.parent)
    table = pa.Table.from_pandas(df)
    if partition_cols:
        pq.write_to_dataset(table, root_path=str(path), partition_cols=list(partition_cols))
    else:
        pq.write_table(table, str(path))


def read_parquet(path: Path) -> pd.DataFrame:
    if path.is_dir():
        return pq.ParquetDataset(str(path)).read_pandas().to_pandas()
    return pd.read_parquet(path)


def list_parquet_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(root.glob("**/*.parquet"))
