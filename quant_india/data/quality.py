from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List

import pandas as pd


@dataclass
class QualityIssue:
    level: str
    message: str
    context: dict


def check_missing_timestamps(df: pd.DataFrame, expected_count: int) -> List[QualityIssue]:
    issues: List[QualityIssue] = []
    grouped = df.groupby("symbol")
    for symbol, group in grouped:
        count = group["timestamp"].nunique()
        if count < expected_count:
            issues.append(
                QualityIssue(
                    level="warning",
                    message=f"Missing timestamps for {symbol}: {count}/{expected_count}",
                    context={"symbol": symbol, "count": count, "expected": expected_count},
                )
            )
    return issues


def check_price_sanity(df: pd.DataFrame, max_jump_pct: float = 0.3) -> List[QualityIssue]:
    issues: List[QualityIssue] = []
    df = df.sort_values(["symbol", "timestamp"])
    df["prev_close"] = df.groupby("symbol")["close"].shift(1)
    df["jump"] = (df["close"] - df["prev_close"]) / df["prev_close"]
    mask = df["prev_close"].notna() & (df["jump"].abs() > max_jump_pct)
    for _, row in df[mask].iterrows():
        issues.append(
            QualityIssue(
                level="critical",
                message=f"Price jump {row['jump']:.2%} exceeds threshold",
                context={"symbol": row["symbol"], "timestamp": row["timestamp"].isoformat()},
            )
        )
    return issues


def run_quality_checks(df: pd.DataFrame, expected_count: int) -> List[QualityIssue]:
    issues = []
    issues.extend(check_missing_timestamps(df, expected_count))
    issues.extend(check_price_sanity(df))
    return issues
