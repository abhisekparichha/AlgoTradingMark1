from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

import pandas as pd

from quant_india.features.feature_store import FeatureStore
from quant_india.features.registry import REGISTRY, FeatureDefinition, get_feature


@dataclass
class FeatureBuildResult:
    feature_name: str
    dataframe: pd.DataFrame


class FeatureBuilder:
    def __init__(self, feature_store: Optional[FeatureStore] = None):
        self.feature_store = feature_store or FeatureStore()

    def available_features(self) -> list[str]:
        return list(REGISTRY.keys())

    def build(
        self,
        data: pd.DataFrame,
        feature_names: Optional[Iterable[str]] = None,
        persist: bool = True,
    ) -> list[FeatureBuildResult]:
        if "symbol" not in data.columns or "timestamp" not in data.columns:
            raise ValueError("Dataframe must include symbol and timestamp columns")
        feature_names = list(feature_names or self.available_features())
        results: list[FeatureBuildResult] = []
        for feature_name in feature_names:
            definition = get_feature(feature_name)
            df_for_feature = self._ensure_inputs(data, definition)
            feature_df = definition.function(df_for_feature)
            if persist:
                self._persist(feature_name, feature_df)
            results.append(FeatureBuildResult(feature_name=feature_name, dataframe=feature_df))
        return results

    def _ensure_inputs(self, data: pd.DataFrame, definition: FeatureDefinition) -> pd.DataFrame:
        missing = [col for col in definition.inputs if col and col not in data.columns and col != "timestamp"]
        if missing:
            raise ValueError(f"Missing columns {missing} for feature {definition.name}")
        return data

    def _persist(self, feature_name: str, feature_df: pd.DataFrame) -> None:
        required_cols = {"symbol", "timestamp"}
        if not required_cols.issubset(feature_df.columns):
            raise ValueError(f"Feature dataframe {feature_name} missing required cols {required_cols}")
        value_cols = [col for col in feature_df.columns if col not in required_cols]
        for symbol, group in feature_df.groupby("symbol"):
            store_df = group.copy()
            store_df = store_df[["timestamp", *value_cols]]
            self.feature_store.write(feature_name=feature_name, symbol=symbol, df=store_df)
