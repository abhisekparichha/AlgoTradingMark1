from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple

import numpy as np
import pandas as pd

from quant_india.models.evaluation import compute_metrics
from quant_india.models.pipelines import TrainingPipeline


@dataclass
class WalkForwardResult:
    window_start: pd.Timestamp
    window_end: pd.Timestamp
    metrics: Dict[str, float]


def walk_forward_validation(
    pipeline: TrainingPipeline,
    data: pd.DataFrame,
    feature_cols: Iterable[str],
    target_col: str,
    window_size: int,
    step_size: int,
) -> List[WalkForwardResult]:
    results: List[WalkForwardResult] = []
    num_rows = len(data)
    start_idx = 0
    while start_idx + window_size + step_size < num_rows:
        train_slice = data.iloc[start_idx : start_idx + window_size]
        test_slice = data.iloc[start_idx + window_size : start_idx + window_size + step_size]
        X_train = train_slice[feature_cols].values
        y_train = train_slice[target_col].values
        X_test = test_slice[feature_cols].values
        y_test = test_slice[target_col].values
        pipeline.fit(X_train, y_train)
        preds = pipeline.model.predict(X_test)
        pnl = y_test * np.sign(preds)
        metrics = compute_metrics(pd.Series(pnl))
        metrics["window_mse"] = float(((preds - y_test) ** 2).mean())
        results.append(
            WalkForwardResult(
                window_start=test_slice["timestamp"].iloc[0],
                window_end=test_slice["timestamp"].iloc[-1],
                metrics=metrics,
            )
        )
        start_idx += step_size
    return results
