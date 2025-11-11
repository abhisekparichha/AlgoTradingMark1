from __future__ import annotations

from typing import Iterable, List

import pandas as pd


def assemble_feature_matrix(
    price_df: pd.DataFrame,
    feature_frames: Iterable[pd.DataFrame],
    horizon: int = 5,
    min_periods: int = 30,
) -> pd.DataFrame:
    """
    Merge feature frames with price data and compute forward-looking targets.
    """
    merged = price_df[["symbol", "timestamp", "close"]].drop_duplicates().copy()
    for frame in feature_frames:
        value_cols = [col for col in frame.columns if col not in {"symbol", "timestamp"}]
        merged = merged.merge(frame, on=["symbol", "timestamp"], how="left")
        merged[value_cols] = merged[value_cols].fillna(method="ffill")
    merged = merged.sort_values(["symbol", "timestamp"]).reset_index(drop=True)
    merged["future_close"] = (
        merged.groupby("symbol")["close"].shift(-horizon)
    )
    merged["target_return"] = merged["future_close"] / merged["close"] - 1
    merged = merged.dropna(subset=["target_return"])
    feature_cols = [col for col in merged.columns if col not in {"future_close"}]
    return merged[feature_cols]
