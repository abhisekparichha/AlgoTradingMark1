from __future__ import annotations

import numpy as np
import pandas as pd

from quant_india.features.registry import register_feature


def _base(df: pd.DataFrame) -> pd.DataFrame:
    return df.sort_values(["symbol", "timestamp"]).reset_index(drop=True)


def _result(df: pd.DataFrame, column: str) -> pd.DataFrame:
    return df[["symbol", "timestamp", column]].copy()


@register_feature(
    name="return_1m",
    description="1-minute log return",
    inputs=["close"],
    tags=["intraday", "momentum"],
)
def return_1m(df: pd.DataFrame) -> pd.DataFrame:
    sorted_df = _base(df)
    log_close = np.log(sorted_df["close"])
    sorted_df["return_1m"] = log_close.groupby(sorted_df["symbol"]).diff()
    return _result(sorted_df, "return_1m")


@register_feature(
    name="return_5m",
    description="5-minute log return",
    inputs=["close"],
    tags=["intraday", "momentum"],
)
def return_5m(df: pd.DataFrame) -> pd.DataFrame:
    sorted_df = _base(df)
    log_close = np.log(sorted_df["close"])
    sorted_df["return_5m"] = log_close.groupby(sorted_df["symbol"]).diff(periods=5)
    return _result(sorted_df, "return_5m")


@register_feature(
    name="return_15m",
    description="15-minute log return",
    inputs=["close"],
    tags=["intraday", "momentum"],
)
def return_15m(df: pd.DataFrame) -> pd.DataFrame:
    sorted_df = _base(df)
    log_close = np.log(sorted_df["close"])
    sorted_df["return_15m"] = log_close.groupby(sorted_df["symbol"]).diff(periods=15)
    return _result(sorted_df, "return_15m")


@register_feature(
    name="realized_vol_5m",
    description="Rolling 5-minute realized volatility (annualized)",
    inputs=["close"],
    tags=["intraday", "volatility"],
)
def realized_vol_5m(df: pd.DataFrame) -> pd.DataFrame:
    sorted_df = _base(df)
    returns = np.log(sorted_df["close"]).groupby(sorted_df["symbol"]).diff()
    grouped = returns.groupby(sorted_df["symbol"])
    vol = grouped.rolling(window=5, min_periods=5).std().reset_index(level=0, drop=True)
    sorted_df["realized_vol_5m"] = vol * np.sqrt(252 * 6.5 * 60)
    return _result(sorted_df, "realized_vol_5m")


@register_feature(
    name="atr_30m",
    description="Rolling 30-minute Average True Range",
    inputs=["high", "low", "close"],
    tags=["intraday", "volatility"],
)
def atr_30m(df: pd.DataFrame) -> pd.DataFrame:
    sorted_df = _base(df)
    high_low = sorted_df["high"] - sorted_df["low"]
    high_prev_close = (sorted_df["high"] - sorted_df.groupby("symbol")["close"].shift(1)).abs()
    low_prev_close = (sorted_df["low"] - sorted_df.groupby("symbol")["close"].shift(1)).abs()
    true_range = pd.concat([high_low, high_prev_close, low_prev_close], axis=1).max(axis=1)
    atr = (
        true_range.groupby(sorted_df["symbol"])
        .rolling(window=30, min_periods=5)
        .mean()
        .reset_index(level=0, drop=True)
    )
    sorted_df["atr_30m"] = atr
    return _result(sorted_df, "atr_30m")


@register_feature(
    name="vwap_deviation",
    description="Deviation from VWAP scaled by rolling std",
    inputs=["close", "volume"],
    tags=["intraday", "mean_reversion"],
)
def vwap_deviation(df: pd.DataFrame) -> pd.DataFrame:
    sorted_df = _base(df)
    group = sorted_df.groupby("symbol")
    cum_turnover = group.apply(lambda g: (g["close"] * g["volume"]).cumsum())
    cum_volume = group["volume"].cumsum().replace(0, np.nan)
    vwap = cum_turnover.values / cum_volume.values
    rolling_std = group["close"].transform(lambda s: s.rolling(window=30, min_periods=5).std())
    sorted_df["vwap_deviation"] = (sorted_df["close"] - vwap) / rolling_std
    return _result(sorted_df, "vwap_deviation")


@register_feature(
    name="volume_zscore",
    description="Volume z-score versus 20 periods",
    inputs=["volume"],
    tags=["intraday", "liquidity"],
)
def volume_zscore(df: pd.DataFrame) -> pd.DataFrame:
    sorted_df = _base(df)
    group = sorted_df.groupby("symbol")["volume"]
    mean = group.transform(lambda s: s.rolling(window=20, min_periods=5).mean())
    std = group.transform(lambda s: s.rolling(window=20, min_periods=5).std())
    sorted_df["volume_zscore"] = (sorted_df["volume"] - mean) / std
    return _result(sorted_df, "volume_zscore")


@register_feature(
    name="bid_ask_spread_bps",
    description="Bid-ask spread in basis points",
    inputs=["bid_price", "ask_price"],
    tags=["microstructure", "liquidity"],
)
def bid_ask_spread_bps(df: pd.DataFrame) -> pd.DataFrame:
    sorted_df = _base(df)
    if "bid_price" not in sorted_df.columns or "ask_price" not in sorted_df.columns:
        sorted_df["bid_ask_spread_bps"] = np.nan
    else:
        mid = (sorted_df["bid_price"] + sorted_df["ask_price"]) / 2
        sorted_df["bid_ask_spread_bps"] = (sorted_df["ask_price"] - sorted_df["bid_price"]) / mid * 10_000
    return _result(sorted_df, "bid_ask_spread_bps")


@register_feature(
    name="depth_imbalance",
    description="Top of book depth imbalance",
    inputs=["bid_qty", "ask_qty"],
    tags=["microstructure"],
)
def depth_imbalance(df: pd.DataFrame) -> pd.DataFrame:
    sorted_df = _base(df)
    if "bid_qty" not in sorted_df.columns or "ask_qty" not in sorted_df.columns:
        sorted_df["depth_imbalance"] = np.nan
    else:
        total = sorted_df["bid_qty"] + sorted_df["ask_qty"]
        sorted_df["depth_imbalance"] = (sorted_df["bid_qty"] - sorted_df["ask_qty"]) / total.replace(0, np.nan)
    return _result(sorted_df, "depth_imbalance")


@register_feature(
    name="overnight_return",
    description="Close to next open return",
    inputs=["open", "close"],
    tags=["overnight"],
)
def overnight_return(df: pd.DataFrame) -> pd.DataFrame:
    sorted_df = _base(df)
    prev_close = sorted_df.groupby("symbol")["close"].shift(1)
    sorted_df["overnight_return"] = (sorted_df["open"] - prev_close) / prev_close
    return _result(sorted_df, "overnight_return")


@register_feature(
    name="time_of_day_sin",
    description="Sine of intraday time",
    inputs=["timestamp"],
    tags=["seasonality"],
)
def time_of_day_sin(df: pd.DataFrame) -> pd.DataFrame:
    sorted_df = _base(df)
    minutes = (
        sorted_df["timestamp"].dt.tz_convert("Asia/Kolkata").dt.hour * 60
        + sorted_df["timestamp"].dt.tz_convert("Asia/Kolkata").dt.minute
    )
    normalized = 2 * np.pi * minutes / (6.5 * 60)
    sorted_df["time_of_day_sin"] = np.sin(normalized)
    return _result(sorted_df, "time_of_day_sin")


@register_feature(
    name="time_of_day_cos",
    description="Cosine of intraday time",
    inputs=["timestamp"],
    tags=["seasonality"],
)
def time_of_day_cos(df: pd.DataFrame) -> pd.DataFrame:
    sorted_df = _base(df)
    minutes = (
        sorted_df["timestamp"].dt.tz_convert("Asia/Kolkata").dt.hour * 60
        + sorted_df["timestamp"].dt.tz_convert("Asia/Kolkata").dt.minute
    )
    normalized = 2 * np.pi * minutes / (6.5 * 60)
    sorted_df["time_of_day_cos"] = np.cos(normalized)
    return _result(sorted_df, "time_of_day_cos")


@register_feature(
    name="cross_section_rank_return_1m",
    description="Cross-sectional rank of 1-minute return",
    inputs=["return_1m"],
    tags=["cross_section"],
)
def cross_section_rank_return_1m(df: pd.DataFrame) -> pd.DataFrame:
    if "return_1m" not in df.columns:
        raise ValueError("return_1m must be computed before cross-sectional rank")
    sorted_df = _base(df)
    rank = sorted_df.groupby("timestamp")["return_1m"].rank(pct=True) - 0.5
    sorted_df["cross_section_rank_return_1m"] = rank
    return _result(sorted_df, "cross_section_rank_return_1m")


@register_feature(
    name="sector_momentum",
    description="Average 15-minute return across sector",
    inputs=["return_15m", "sector"],
    tags=["cross_section"],
)
def sector_momentum(df: pd.DataFrame) -> pd.DataFrame:
    sorted_df = _base(df)
    if "sector" not in sorted_df.columns or "return_15m" not in sorted_df.columns:
        sorted_df["sector_momentum"] = np.nan
    else:
        grouped = (
            sorted_df.groupby(["timestamp", "sector"])["return_15m"]
            .mean()
            .rename("sector_momentum")
            .reset_index()
        )
        sorted_df = sorted_df.merge(grouped, on=["timestamp", "sector"], how="left")
    return _result(sorted_df, "sector_momentum")


@register_feature(
    name="iv_level",
    description="Implied volatility level",
    inputs=["iv"],
    tags=["derivatives"],
)
def iv_level(df: pd.DataFrame) -> pd.DataFrame:
    sorted_df = _base(df)
    sorted_df["iv_level"] = sorted_df.get("iv", np.nan)
    return _result(sorted_df, "iv_level")


@register_feature(
    name="iv_skew",
    description="Put-call IV skew",
    inputs=["iv_call", "iv_put"],
    tags=["derivatives"],
)
def iv_skew(df: pd.DataFrame) -> pd.DataFrame:
    sorted_df = _base(df)
    if "iv_call" not in sorted_df.columns or "iv_put" not in sorted_df.columns:
        sorted_df["iv_skew"] = np.nan
    else:
        sorted_df["iv_skew"] = sorted_df["iv_put"] - sorted_df["iv_call"]
    return _result(sorted_df, "iv_skew")


@register_feature(
    name="put_call_ratio_change",
    description="Change in put-call ratio",
    inputs=["put_call_ratio"],
    tags=["derivatives"],
)
def put_call_ratio_change(df: pd.DataFrame) -> pd.DataFrame:
    sorted_df = _base(df)
    if "put_call_ratio" not in sorted_df.columns:
        sorted_df["put_call_ratio_change"] = np.nan
    else:
        sorted_df["put_call_ratio_change"] = sorted_df.groupby("symbol")["put_call_ratio"].diff()
    return _result(sorted_df, "put_call_ratio_change")


@register_feature(
    name="fii_flow_normalized",
    description="Normalized FII net flow",
    inputs=["fii_net"],
    tags=["macro"],
)
def fii_flow_normalized(df: pd.DataFrame) -> pd.DataFrame:
    sorted_df = _base(df)
    if "fii_net" not in sorted_df.columns:
        sorted_df["fii_flow_normalized"] = np.nan
    else:
        series = sorted_df["fii_net"]
        sorted_df["fii_flow_normalized"] = (series - series.mean()) / series.std(ddof=0)
    return _result(sorted_df, "fii_flow_normalized")


@register_feature(
    name="news_sentiment_score",
    description="News sentiment aggregated score",
    inputs=["sentiment_score"],
    tags=["news"],
)
def news_sentiment_score(df: pd.DataFrame) -> pd.DataFrame:
    sorted_df = _base(df)
    sorted_df["news_sentiment_score"] = sorted_df.get("sentiment_score", np.nan)
    return _result(sorted_df, "news_sentiment_score")


@register_feature(
    name="news_shock",
    description="Binary flag for high severity news events",
    inputs=["event_severity"],
    tags=["news", "risk"],
)
def news_shock(df: pd.DataFrame) -> pd.DataFrame:
    sorted_df = _base(df)
    if "event_severity" not in sorted_df.columns:
        sorted_df["news_shock"] = 0
    else:
        sorted_df["news_shock"] = (sorted_df["event_severity"] >= 0.8).astype(int)
    return _result(sorted_df, "news_shock")


@register_feature(
    name="liquidity_score",
    description="Liquidity score scaled by ADV",
    inputs=["volume"],
    tags=["risk"],
)
def liquidity_score(df: pd.DataFrame) -> pd.DataFrame:
    sorted_df = _base(df)
    group = sorted_df.groupby("symbol")["volume"]
    adv = group.transform(lambda s: s.rolling(window=390, min_periods=30).mean())
    max_adv = adv.groupby(sorted_df["symbol"]).transform("max")
    sorted_df["liquidity_score"] = adv / max_adv.replace(0, np.nan)
    return _result(sorted_df, "liquidity_score")


@register_feature(
    name="distance_to_52w_high",
    description="Distance to trailing 52-week high",
    inputs=["close"],
    tags=["trend"],
)
def distance_to_52w_high(df: pd.DataFrame) -> pd.DataFrame:
    sorted_df = _base(df)
    rolling_high = (
        sorted_df.groupby("symbol")["close"]
        .transform(lambda s: s.rolling(window=252 * 390, min_periods=390).max())
    )
    sorted_df["distance_to_52w_high"] = sorted_df["close"] / rolling_high - 1
    return _result(sorted_df, "distance_to_52w_high")
