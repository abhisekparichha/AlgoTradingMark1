from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

import numpy as np
import pandas as pd
from sklearn.metrics import mean_squared_error
from sklearn.model_selection import TimeSeriesSplit

from quant_india.models.evaluation import compute_metrics
from quant_india.models.estimators import EnsembleModel, LSTMAlphaModel, XGBoostAlphaModel


@dataclass
class TrainingPipeline:
    model: EnsembleModel
    n_splits: int = 5

    def cross_validate(self, X: np.ndarray, y: np.ndarray) -> Dict[str, float]:
        splitter = TimeSeriesSplit(n_splits=self.n_splits)
        mses = []
        for train_idx, test_idx in splitter.split(X):
            X_train, X_test = X[train_idx], X[test_idx]
            y_train, y_test = y[train_idx], y[test_idx]
            self.model.fit(X_train, y_train)
            preds = self.model.predict(X_test)
            mses.append(mean_squared_error(y_test, preds))
        return {"cv_mse": float(np.mean(mses))}

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        self.model.fit(X, y)

    def evaluate(self, X: np.ndarray, y: np.ndarray) -> Dict[str, float]:
        preds = self.model.predict(X)
        residual_returns = y * np.sign(preds)
        metrics = compute_metrics(pd.Series(residual_returns))
        metrics["mse"] = mean_squared_error(y, preds)
        return metrics


def default_training_pipeline(params: Optional[dict] = None) -> TrainingPipeline:
    xgb_model = XGBoostAlphaModel(params=params or {})
    lstm_model = LSTMAlphaModel()
    ensemble = EnsembleModel(xgb_model=xgb_model, lstm_model=lstm_model)
    return TrainingPipeline(model=ensemble)
