from __future__ import annotations

from pathlib import Path
from typing import Dict

import pandas as pd

from quant_india.common.utils import dump_json


def generate_daily_report(pnl_df: pd.DataFrame, output_path: Path) -> Dict[str, float]:
    pnl_df["date"] = pnl_df["timestamp"].dt.tz_convert("Asia/Kolkata").dt.date
    daily = pnl_df.groupby("date")["net_pnl"].sum()
    cumulative = (1 + pnl_df["net_pnl"]).cumprod()
    drawdown = cumulative / cumulative.cummax() - 1
    report = {
        "total_days": int(daily.count()),
        "avg_daily_pnl": float(daily.mean()),
        "max_drawdown": float(drawdown.min()),
        "last_day_pnl": float(daily.iloc[-1] if not daily.empty else 0.0),
    }
    dump_json(report, output_path)
    return report
