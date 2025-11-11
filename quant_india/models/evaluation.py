from __future__ import annotations

import numpy as np
import pandas as pd


def compute_metrics(returns: pd.Series, periods_per_year: int = 252 * 390) -> dict:
    returns = returns.dropna()
    if returns.empty:
        return {"cagr": 0.0, "sharpe": 0.0, "max_drawdown": 0.0}
    cumulative = (1 + returns).cumprod()
    total_return = cumulative.iloc[-1] - 1
    years = len(returns) / periods_per_year
    cagr = (1 + total_return) ** (1 / max(years, 1e-6)) - 1
    sharpe = np.sqrt(periods_per_year) * returns.mean() / (returns.std(ddof=0) + 1e-9)
    running_max = cumulative.cummax()
    drawdown = cumulative / running_max - 1
    max_drawdown = drawdown.min()
    return {"cagr": cagr, "sharpe": sharpe, "max_drawdown": max_drawdown}
