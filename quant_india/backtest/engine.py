from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

import numpy as np
import pandas as pd

from quant_india.backtest.cost_models import CostModel
from quant_india.models.evaluation import compute_metrics


@dataclass
class BacktestResult:
    pnl: pd.DataFrame
    metrics: Dict[str, float]


class BacktestEngine:
    def __init__(self, cost_model: Optional[CostModel] = None):
        self.cost_model = cost_model or CostModel()

    def run(self, price_df: pd.DataFrame, signals_df: pd.DataFrame) -> BacktestResult:
        data = price_df.merge(signals_df, on=["symbol", "timestamp"], how="left")
        data = data.sort_values(["symbol", "timestamp"]).fillna(method="ffill")
        data["signal"] = data["signal"].fillna(0)
        data["returns"] = data.groupby("symbol")["close"].pct_change().fillna(0)
        data["position"] = data.groupby("symbol")["signal"].shift(1).fillna(0)
        data["gross_pnl"] = data["position"] * data["returns"]
        data["turnover"] = data.groupby("symbol")["position"].diff().abs().fillna(0)
        cost_pct = (
            self.cost_model.brokerage_pct + self.cost_model.stamp_duty_pct + self.cost_model.exchange_charges_pct
        )
        trade_notional = data["turnover"] * data["close"]
        spread_bps = data.get("bid_ask_spread_bps", pd.Series(10, index=data.index))
        spread_value = (spread_bps / 10_000) * data["close"]
        data["cost"] = trade_notional * cost_pct + self.cost_model.slippage_factor * spread_value
        data["net_pnl"] = data["gross_pnl"] - data["cost"] / data["close"].replace(0, np.nan)
        metrics = compute_metrics(data.groupby("timestamp")["net_pnl"].mean())
        return BacktestResult(pnl=data, metrics=metrics)
