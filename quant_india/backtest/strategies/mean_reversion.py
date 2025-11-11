from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class MeanReversionStrategy:
    entry_threshold: float = -1.0
    exit_threshold: float = 0.0
    max_position: int = 1

    def generate_signals(self, features: pd.DataFrame) -> pd.DataFrame:
        df = features.sort_values(["symbol", "timestamp"]).copy()
        if "vwap_deviation" not in df.columns:
            raise ValueError("Feature vwap_deviation required for mean reversion strategy")
        df["signal"] = 0
        long_entries = df["vwap_deviation"] < self.entry_threshold
        exits = df["vwap_deviation"] > self.exit_threshold
        df.loc[long_entries, "signal"] = 1
        df.loc[exits, "signal"] = 0
        df["signal"] = (
            df.groupby("symbol")["signal"]
            .apply(lambda s: s.replace(to_replace=0, method="ffill"))
            .fillna(0)
            .clip(-self.max_position, self.max_position)
        )
        return df[["symbol", "timestamp", "signal"]]
