from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import joblib
import numpy as np
import xgboost as xgb


@dataclass
class XGBoostAlphaModel:
    params: dict
    model: Optional[xgb.XGBRegressor] = None

    def __post_init__(self) -> None:
        default_params = {
            "n_estimators": 200,
            "max_depth": 4,
            "learning_rate": 0.1,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "reg_lambda": 1.0,
            "objective": "reg:squarederror",
        }
        merged = {**default_params, **self.params}
        self.model = xgb.XGBRegressor(**merged)

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        if self.model is None:
            raise ValueError("Model not initialized")
        self.model.fit(X, y)

    def predict(self, X: np.ndarray) -> np.ndarray:
        if self.model is None:
            raise ValueError("Model not trained")
        return self.model.predict(X)

    def save(self, path: Path) -> None:
        joblib.dump(self.model, path)

    def load(self, path: Path) -> None:
        self.model = joblib.load(path)


class LSTMAlphaModel:
    """
    Skeleton LSTM forecaster. Replace with production-grade sequence model.
    Currently returns zero predictions to serve as integration placeholder.
    """

    def __init__(self, input_size: Optional[int] = None, horizon: int = 5):
        self.input_size = input_size
        self.horizon = horizon

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        self.input_size = X.shape[1]
        # TODO: Implement PyTorch-based LSTM training loop.

    def predict(self, X: np.ndarray) -> np.ndarray:
        if self.input_size is None:
            self.input_size = X.shape[1]
        return np.zeros(X.shape[0])


class EnsembleModel:
    def __init__(self, xgb_model: XGBoostAlphaModel, lstm_model: LSTMAlphaModel, weights: tuple[float, float] = (0.7, 0.3)):
        self.xgb_model = xgb_model
        self.lstm_model = lstm_model
        self.weights = weights

    def fit(self, X: np.ndarray, y: np.ndarray) -> None:
        self.xgb_model.fit(X, y)
        self.lstm_model.fit(X, y)

    def predict(self, X: np.ndarray) -> np.ndarray:
        xgb_preds = self.xgb_model.predict(X)
        lstm_preds = self.lstm_model.predict(X)
        w1, w2 = self.weights
        return w1 * xgb_preds + w2 * lstm_preds
