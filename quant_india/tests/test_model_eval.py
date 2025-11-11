import numpy as np
import pandas as pd

from quant_india.features import FeatureBuilder
from quant_india.models import assemble_feature_matrix, default_training_pipeline


def test_training_pipeline_runs():
    symbols = ["INFY", "TCS"]
    timestamps = pd.date_range(
        start=pd.Timestamp("2024-01-01 09:15", tz="Asia/Kolkata"),
        periods=120,
        freq="1min",
    ).tz_convert("UTC")
    price_rows = []
    for symbol in symbols:
        base_price = 100 + np.random.rand()
        prices = base_price + np.cumsum(np.random.normal(0, 0.1, size=len(timestamps)))
        for ts, price in zip(timestamps, prices):
            price_rows.append({"symbol": symbol, "timestamp": ts, "open": price, "high": price + 0.1, "low": price - 0.1, "close": price, "volume": 1000})
    price_df = pd.DataFrame(price_rows)
    builder = FeatureBuilder()
    features = builder.build(price_df, feature_names=["return_1m", "volume_zscore"], persist=False)
    dataset = assemble_feature_matrix(price_df, [result.dataframe for result in features], horizon=5)
    feature_cols = [col for col in dataset.columns if col not in {"symbol", "timestamp", "close", "target_return"}]
    X = dataset[feature_cols].fillna(0).values
    y = dataset["target_return"].values
    pipeline = default_training_pipeline()
    metrics = pipeline.cross_validate(X, y)
    assert "cv_mse" in metrics
