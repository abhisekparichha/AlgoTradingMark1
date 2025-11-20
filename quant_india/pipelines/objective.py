from __future__ import annotations

import hashlib
import json
import math
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from quant_india.models.evaluation import compute_metrics


NIFTY500_SAMPLE = [
    "RELIANCE",
    "TCS",
    "INFY",
    "HDFCBANK",
    "ICICIBANK",
    "KOTAKBANK",
    "AXISBANK",
    "SBIN",
    "LT",
    "ITC",
    "HINDUNILVR",
    "ASIANPAINT",
    "ULTRACEMCO",
    "GRASIM",
    "ADANIENT",
    "ADANIPORTS",
    "BHARTIARTL",
    "BAJFINANCE",
    "BAJAJFINSV",
    "MARUTI",
    "M&M",
    "TITAN",
    "SUNPHARMA",
    "DRREDDY",
    "CIPLA",
    "DIVISLAB",
    "NESTLEIND",
    "HEROMOTOCO",
    "EICHERMOT",
    "POWERGRID",
    "NTPC",
    "ONGC",
    "COALINDIA",
    "BPCL",
    "HCLTECH",
    "TECHM",
    "LTIM",
    "WIPRO",
    "BRITANNIA",
    "JSWSTEEL",
    "TATASTEEL",
    "HINDALCO",
    "VEDL",
    "APOLLOHOSP",
    "DMART",
    "ICICIPRULI",
    "ICICIGI",
    "SBILIFE",
    "HDFCLIFE",
    "PIDILITIND",
    "DABUR",
    "UBL",
    "GODREJCP",
    "COLPAL",
    "PNB",
    "BANKBARODA",
    "INDUSINDBK",
    "YESBANK",
    "BANDHANBNK",
    "FEDERALBNK",
    "CANBK",
    "IDFCFIRSTB",
    "MUTHOOTFIN",
    "PEL",
    "AMBUJACEM",
    "ACC",
    "BHEL",
    "IRCTC",
    "ZOMATO",
    "PAYTM",
    "NYKAA",
    "POLYCAB",
    "ABBOTINDIA",
    "PAGEIND",
    "JUBLFOOD",
    "MANAPPURAM",
    "ZEEL",
    "INDIGO",
    "LUPIN",
    "TORNTPHARM",
    "BOSCHLTD",
    "BERGEPAINT",
    "AUBANK",
    "CHOLAFIN",
    "SHREECEM",
    "NAVINFLUOR",
    "ALKEM",
    "TRENT",
    "TVSMOTOR",
    "UPL",
    "BATAINDIA",
]


def _utc_now() -> pd.Timestamp:
    ts = pd.Timestamp.utcnow()
    return ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")


def _normalize(series: pd.Series) -> pd.Series:
    if series.empty:
        return series
    min_val = series.min()
    max_val = series.max()
    if math.isclose(max_val, min_val):
        return pd.Series(0.5, index=series.index)
    return (series - min_val) / (max_val - min_val + 1e-12)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _max_drawdown(series: pd.Series) -> float:
    if series.empty:
        return 0.0
    cumulative = series.cummax()
    drawdown = series / cumulative - 1
    return float(drawdown.min())


@dataclass
class ObjectiveConfig:
    data_root: Path = Path("artifacts/data_repo")
    model_artifact_dir: Path = Path("artifacts/model_outputs")
    max_total_invest: float = 100_000.0
    shortlist_n: int = 30
    selection_mode: str = "signal-rank"
    selection_k: int = 3
    min_adv_inr: float = 10_000_000.0
    min_daily_vol: float = 100_000.0
    entry_threshold: float = 0.6
    exit_threshold: float = -0.2
    target_pct: float = 0.03
    stop_pct: float = 0.015
    commission_pct: float = 0.0003
    min_brokerage: float = 20.0
    gst_pct: float = 0.18 * 0.0003
    exchange_fees_pct: float = 0.00002
    slippage_mean: float = 0.0005
    slippage_sd: float = 0.001
    max_spread_pct: float = 0.01
    max_holding_minutes: int = 240
    liquidity_threshold: float = 0.35
    shortlist_liquidity_buffer: float = 0.45
    sim_start: Optional[pd.Timestamp] = None
    sim_end: Optional[pd.Timestamp] = None
    random_seed: int = 42
    shortlist_seed: int = 11
    selection_seed: int = 19
    run_date: str = field(default_factory=lambda: _utc_now().strftime("%Y%m%d"))
    custom_ticker_list: Optional[Sequence[str]] = None
    selected_ticker_list: Optional[Sequence[str]] = None
    universe_size: int = 80
    intraday_lookback_days: int = 252
    adv_lookback_days: int = 126
    volatility_lookback_days: int = 30
    momentum_lookback_days: int = 63


@dataclass
class SelectionPlan:
    symbol: str
    quantity: int
    lot_size: int
    entry_price: float
    position_value: float
    liquidity_score: float
    volatility_score: float
    momentum_score: float
    stability_score: float


@dataclass
class DataBundle:
    daily_df: pd.DataFrame
    intraday_df: pd.DataFrame
    manifest_path: Path
    latest_prices: pd.Series
    holiday_df: pd.DataFrame


def run_objective_pipeline(config: ObjectiveConfig) -> Dict[str, str]:
    runner = ObjectiveRunner(config)
    return runner.run()


class ObjectiveRunner:
    def __init__(self, config: ObjectiveConfig):
        self.cfg = config
        self.data_root = self.cfg.data_root
        self.artifact_dir = self.cfg.model_artifact_dir
        self.data_root.mkdir(parents=True, exist_ok=True)
        self.artifact_dir.mkdir(parents=True, exist_ok=True)
        self.sim_end = (self.cfg.sim_end or _utc_now()).floor("min")
        default_start = self.sim_end - pd.Timedelta(days=182)
        self.sim_start = (self.cfg.sim_start or default_start).floor("min")
        if self.sim_start >= self.sim_end:
            raise ValueError("sim_start must be before sim_end")
        self.rng = np.random.default_rng(self.cfg.random_seed)

    def run(self) -> Dict[str, str]:
        data_bundle = self._create_data_repository()
        shortlist_df = self._build_shortlist(data_bundle.daily_df)
        selection = self._select_stocks(shortlist_df, data_bundle.latest_prices)
        score_df = self._prepare_intraday_frame(data_bundle.intraday_df, selection)
        trades_df, equity_curve_df, portfolio_metrics, diagnostics = self._simulate(score_df, selection)
        return self._write_artifacts(
            shortlist_df=shortlist_df,
            selection=selection,
            trades_df=trades_df,
            equity_curve_df=equity_curve_df,
            portfolio_metrics=portfolio_metrics,
            diagnostics=diagnostics,
            manifest_path=data_bundle.manifest_path,
        )

    # ------------------------------------------------------------------
    # Step 1: Create data repository
    # ------------------------------------------------------------------
    def _create_data_repository(self) -> DataBundle:
        raw_daily = self.data_root / "raw" / "daily"
        raw_intraday = self.data_root / "raw" / "intraday"
        meta_dir = self.data_root / "meta"
        corp_dir = self.data_root / "corporate_actions"
        embeddings_dir = self.data_root / "embeddings"
        for path in (raw_daily, raw_intraday, meta_dir, corp_dir, embeddings_dir):
            path.mkdir(parents=True, exist_ok=True)

        universe = self._select_universe()
        daily_start = (self.sim_end - pd.DateOffset(years=5)).normalize()
        intraday_start = self.sim_end - pd.Timedelta(days=self.cfg.intraday_lookback_days)

        daily_df = self._generate_daily_prices(
            universe=universe,
            start_date=daily_start,
            end_date=self.sim_end.normalize(),
        )
        daily_path = raw_daily / "daily_prices.parquet"
        daily_df.to_parquet(daily_path, index=False)

        intraday_df = self._generate_intraday_prices(
            daily_df=daily_df,
            start_ts=intraday_start,
            end_ts=self.sim_end,
        )
        intraday_path = raw_intraday / "intraday_prices.parquet"
        intraday_df.to_parquet(intraday_path, index=False)

        holiday_df = self._build_holiday_calendar()
        holiday_path = meta_dir / "holiday_calendar.csv"
        holiday_df.to_csv(holiday_path, index=False)

        universe_path = meta_dir / "universe.csv"
        pd.DataFrame({"symbol": universe}).to_csv(universe_path, index=False)

        halts_path = meta_dir / "trading_halts.csv"
        pd.DataFrame(columns=["symbol", "halt_date", "reason"]).to_csv(halts_path, index=False)

        corporate_actions_df = self._generate_corporate_actions(universe)
        corporate_actions_path = corp_dir / "corporate_actions.csv"
        corporate_actions_df.to_csv(corporate_actions_path, index=False)

        embeddings_df = self._generate_embeddings(universe[: min(10, len(universe))])
        embeddings_path = embeddings_dir / "news_embeddings.parquet"
        embeddings_df.to_parquet(embeddings_path, index=False)

        manifest_entries = [
            self._manifest_entry(daily_path, len(daily_df), timestamp_col="timestamp", df=daily_df),
            self._manifest_entry(intraday_path, len(intraday_df), timestamp_col="timestamp", df=intraday_df),
            self._manifest_entry(corporate_actions_path, len(corporate_actions_df)),
            self._manifest_entry(holiday_path, len(holiday_df)),
            self._manifest_entry(universe_path, len(universe)),
            self._manifest_entry(embeddings_path, len(embeddings_df)),
        ]

        manifest_path = self.data_root / f"manifest_{self.cfg.run_date}.json"
        manifest_payload = {
            "generated_at": _utc_now().isoformat(),
            "data_root": str(self.data_root.resolve()),
            "files": manifest_entries,
        }
        manifest_path.write_text(json.dumps(manifest_payload, indent=2))

        if daily_df.empty or intraday_df.empty:
            self._write_error("data_error.json", {"reason": "Generated datasets are empty"})
            raise RuntimeError("Data repository generation failed")

        latest_prices = (
            daily_df.sort_values("timestamp").groupby("symbol").tail(1).set_index("symbol")["close"]
        )

        return DataBundle(
            daily_df=daily_df,
            intraday_df=intraday_df,
            manifest_path=manifest_path,
            latest_prices=latest_prices,
            holiday_df=holiday_df,
        )

    def _select_universe(self) -> List[str]:
        if self.cfg.custom_ticker_list:
            symbols = [symbol.upper() for symbol in self.cfg.custom_ticker_list]
        else:
            symbols = NIFTY500_SAMPLE[: self.cfg.universe_size]
        return symbols

    def _generate_daily_prices(self, universe: Sequence[str], start_date: pd.Timestamp, end_date: pd.Timestamp) -> pd.DataFrame:
        start_local = start_date.tz_convert("Asia/Kolkata") if start_date.tzinfo else start_date.tz_localize("Asia/Kolkata")
        end_local = end_date.tz_convert("Asia/Kolkata") if end_date.tzinfo else end_date.tz_localize("Asia/Kolkata")
        trading_days = pd.bdate_range(start=start_local, end=end_local, tz="Asia/Kolkata")
        rows: List[dict] = []
        for symbol in universe:
            base_price = 80 + (hash(symbol) % 900)
            noise = self.rng.normal(0.0005, 0.02, size=len(trading_days))
            prices = base_price * np.exp(np.cumsum(noise))
            volumes = self.rng.integers(200_000, 5_000_000, size=len(trading_days))
            turnovers = volumes * prices
            highs = prices * (1 + np.abs(self.rng.normal(0.001, 0.01, size=len(prices))))
            lows = prices * (1 - np.abs(self.rng.normal(0.001, 0.01, size=len(prices))))
            opens = prices * (1 + self.rng.normal(0, 0.005, size=len(prices)))
            for ts, o, h, l, c, v, t in zip(trading_days, opens, highs, lows, prices, volumes, turnovers, strict=False):
                utc_ts = ts.tz_convert("UTC")
                rows.append(
                    {
                        "symbol": symbol,
                        "timestamp": utc_ts,
                        "date": utc_ts.date().isoformat(),
                        "open": float(max(o, 1)),
                        "high": float(max(h, o, c)),
                        "low": float(min(l, o, c)),
                        "close": float(c),
                        "volume": int(v),
                        "turnover": float(t),
                    }
                )
        return pd.DataFrame(rows)

    def _generate_intraday_prices(
        self, daily_df: pd.DataFrame, start_ts: pd.Timestamp, end_ts: pd.Timestamp
    ) -> pd.DataFrame:
        daily_df = daily_df.copy()
        daily_df["date"] = pd.to_datetime(daily_df["timestamp"]).dt.date
        start_cutoff = start_ts.tz_convert("Asia/Kolkata").date()
        eligible_dates = sorted(
            {date for date in daily_df["date"].unique() if date >= start_cutoff}
        )
        minute_rows: List[dict] = []
        for symbol, symbol_daily in daily_df.groupby("symbol"):
            symbol_daily = symbol_daily.set_index("date")
            for date in eligible_dates:
                if date not in symbol_daily.index:
                    continue
                date_ts = pd.Timestamp(date).tz_localize("Asia/Kolkata")
                if date_ts.tz_convert("UTC") > end_ts:
                    break
                start_minute = date_ts + pd.Timedelta(hours=9, minutes=15)
                end_minute = date_ts + pd.Timedelta(hours=15, minutes=30)
                minutes = pd.date_range(start=start_minute, end=end_minute, freq="1min", tz="Asia/Kolkata")
                prev_close = symbol_daily.loc[date]["close"]
                intraday_noise = self.rng.normal(0, 0.0008, size=len(minutes))
                price_path = prev_close * np.cumprod(1 + intraday_noise)
                scaler = symbol_daily.loc[date]["close"] / price_path[-1]
                price_path *= scaler
                volumes = self.rng.integers(500, 50_000, size=len(minutes))
                for ts, price, vol in zip(minutes, price_path, volumes, strict=False):
                    utc_ts = ts.tz_convert("UTC")
                    if not (self.sim_start <= utc_ts <= end_ts):
                        continue
                    spread = abs(self.rng.normal(self.cfg.slippage_mean, self.cfg.slippage_sd))
                    minute_rows.append(
                        {
                            "symbol": symbol,
                            "timestamp": utc_ts,
                            "open": float(price * (1 - 0.0005)),
                            "high": float(price * (1 + 0.0007)),
                            "low": float(price * (1 - 0.0007)),
                            "close": float(price),
                            "volume": int(vol),
                            "turnover": float(price * vol),
                            "spread_pct": float(np.clip(spread, 0.0002, self.cfg.max_spread_pct)),
                        }
                    )
        return pd.DataFrame(minute_rows)

    def _build_holiday_calendar(self) -> pd.DataFrame:
        base_year = self.sim_end.year
        holidays = [
            (pd.Timestamp(f"{base_year}-01-26"), "Republic Day"),
            (pd.Timestamp(f"{base_year}-03-08"), "Mahashivratri"),
            (pd.Timestamp(f"{base_year}-08-15"), "Independence Day"),
            (pd.Timestamp(f"{base_year}-10-02"), "Gandhi Jayanti"),
            (pd.Timestamp(f"{base_year}-11-01"), "Diwali (Laxmi Pujan)"),
        ]
        return pd.DataFrame({"date": [ts.date().isoformat() for ts, _ in holidays], "description": [desc for _, desc in holidays]})

    def _generate_corporate_actions(self, universe: Sequence[str]) -> pd.DataFrame:
        rows = []
        base_date = self.sim_start.date()
        for symbol in universe[: min(15, len(universe))]:
            rows.append(
                {
                    "symbol": symbol,
                    "ex_date": (pd.Timestamp(base_date) + pd.Timedelta(days=int(self.rng.integers(1, 120)))).date().isoformat(),
                    "action_type": "DIVIDEND",
                    "adjustment_factor": round(float(self.rng.uniform(0.01, 0.05)), 4),
                }
            )
        return pd.DataFrame(rows)

    def _generate_embeddings(self, symbols: Sequence[str]) -> pd.DataFrame:
        embeddings = []
        for symbol in symbols:
            vector = self.rng.normal(0, 1, size=8)
            record = {"symbol": symbol}
            record.update({f"dim_{i}": float(val) for i, val in enumerate(vector)})
            embeddings.append(record)
        return pd.DataFrame(embeddings)

    def _manifest_entry(
        self,
        path: Path,
        rows: int,
        timestamp_col: Optional[str] = None,
        df: Optional[pd.DataFrame] = None,
    ) -> Dict[str, object]:
        entry: Dict[str, object] = {
            "file": str(path.relative_to(self.data_root)),
            "rows": int(rows),
            "last_modified": pd.Timestamp(path.stat().st_mtime, unit="s", tz="UTC").isoformat(),
            "sha256": _sha256(path),
        }
        if timestamp_col and df is not None and not df.empty:
            timestamps = pd.to_datetime(df[timestamp_col], utc=True)
            entry["timestamp_start"] = timestamps.min().isoformat()
            entry["timestamp_end"] = timestamps.max().isoformat()
        return entry

    # ------------------------------------------------------------------
    # Step 2: Shortlist stocks
    # ------------------------------------------------------------------
    def _build_shortlist(self, daily_df: pd.DataFrame) -> pd.DataFrame:
        cutoff = self.sim_end - pd.Timedelta(days=self.cfg.adv_lookback_days)
        mask = pd.to_datetime(daily_df["timestamp"]) >= cutoff
        recent = daily_df.loc[mask].copy()
        if recent.empty:
            raise RuntimeError("Insufficient daily data to build shortlist")
        recent.sort_values(["symbol", "timestamp"], inplace=True)
        recent["return"] = recent.groupby("symbol")["close"].pct_change().fillna(0)
        grouped = recent.groupby("symbol")
        liquidity = grouped["turnover"].median().rename("median_adv_inr")
        avg_volume = grouped["volume"].mean().rename("avg_volume")

        def _volatility(df: pd.DataFrame) -> float:
            rolling = df["return"].rolling(self.cfg.volatility_lookback_days, min_periods=5).std()
            return float(rolling.iloc[-1]) if not rolling.empty else 0.0

        def _momentum(series: pd.Series) -> float:
            if len(series) <= self.cfg.momentum_lookback_days:
                return 0.0
            return float(series.iloc[-1] / series.iloc[-self.cfg.momentum_lookback_days] - 1)

        def _stability(series: pd.Series) -> float:
            return float(_max_drawdown(pd.Series(series.values)))

        vol_metric = grouped.apply(_volatility, include_groups=False).rename("volatility_30d").fillna(0)
        momentum = grouped["close"].apply(_momentum).rename("momentum_3m")
        stability = grouped["close"].apply(_stability).rename("max_drawdown")

        shortlist = pd.concat([liquidity, avg_volume, vol_metric, momentum, stability], axis=1).reset_index()
        shortlist["liquidity_score"] = _normalize(shortlist["median_adv_inr"])
        shortlist["volatility_score"] = _normalize(shortlist["volatility_30d"].replace({np.inf: np.nan}).fillna(0))
        shortlist["momentum_score"] = _normalize(shortlist["momentum_3m"])
        shortlist["stability_score"] = 1 - _normalize(shortlist["max_drawdown"].abs())
        shortlist["composite_score"] = (
            0.35 * shortlist["momentum_score"]
            + 0.35 * shortlist["liquidity_score"]
            + 0.15 * shortlist["stability_score"]
            + 0.15 * (1 - shortlist["volatility_score"])
        )
        shortlist = shortlist[
            (shortlist["median_adv_inr"] >= self.cfg.min_adv_inr)
            & (shortlist["avg_volume"] >= self.cfg.min_daily_vol)
            & (shortlist["liquidity_score"] >= self.cfg.liquidity_threshold)
        ]
        shortlist = shortlist.sort_values("composite_score", ascending=False).head(self.cfg.shortlist_n).reset_index(drop=True)
        if shortlist.empty:
            raise RuntimeError("No symbols met the liquidity filters for shortlist")
        return shortlist

    # ------------------------------------------------------------------
    # Step 3: Selection
    # ------------------------------------------------------------------
    def _select_stocks(self, shortlist: pd.DataFrame, latest_prices: pd.Series) -> List[SelectionPlan]:
        if shortlist.empty:
            raise RuntimeError("Shortlist is empty")
        df = shortlist.copy()
        rng = np.random.default_rng(self.cfg.selection_seed)
        if self.cfg.selection_mode.lower() == "signal-rank":
            df["model_signal"] = (
                0.5 * df["momentum_score"] + 0.3 * df["liquidity_score"] + 0.2 * df["stability_score"]
            ) + rng.normal(0, 0.05, size=len(df))
            selected = df.sort_values("model_signal", ascending=False).head(self.cfg.selection_k)
        elif self.cfg.selection_mode.lower() == "random-sample":
            selected = df.sample(n=min(self.cfg.selection_k, len(df)), random_state=self.cfg.selection_seed)
        elif self.cfg.selection_mode.lower() == "user-defined":
            if not self.cfg.selected_ticker_list:
                raise ValueError("selected_ticker_list required for USER-DEFINED mode")
            symbols = [s.upper() for s in self.cfg.selected_ticker_list]
            selected = df[df["symbol"].isin(symbols)]
        else:
            raise ValueError(f"Unsupported selection_mode {self.cfg.selection_mode}")

        if selected.empty:
            raise RuntimeError("No tickers selected after applying selection mode")

        selection_plans: List[SelectionPlan] = []
        capital_remaining = self.cfg.max_total_invest
        symbols_remaining = len(selected)

        for _, row in selected.iterrows():
            symbol = row["symbol"]
            price = float(latest_prices.get(symbol))
            if math.isnan(price) or price <= 0:
                continue
            lot_size = self._lot_size(price)
            per_symbol_budget = capital_remaining / symbols_remaining
            qty = int(math.floor(per_symbol_budget / (price * lot_size)) * lot_size)
            if qty < lot_size:
                continue
            notional = qty * price
            capital_remaining -= notional
            symbols_remaining -= 1
            selection_plans.append(
                SelectionPlan(
                    symbol=symbol,
                    quantity=qty,
                    lot_size=lot_size,
                    entry_price=price,
                    position_value=notional,
                    liquidity_score=float(row["liquidity_score"]),
                    volatility_score=float(row["volatility_score"]),
                    momentum_score=float(row["momentum_score"]),
                    stability_score=float(row["stability_score"]),
                )
            )
        if not selection_plans:
            self._write_error("allocation_error.json", {"reason": "Unable to size any positions within capital constraints"})
            raise RuntimeError("Sizing failed")
        return selection_plans

    def _lot_size(self, price: float) -> int:
        if price < 200:
            return 100
        if price < 500:
            return 50
        if price < 1000:
            return 25
        if price < 2000:
            return 10
        return 1

    # ------------------------------------------------------------------
    # Step 4 & 5: Simulation and reporting
    # ------------------------------------------------------------------
    def _prepare_intraday_frame(self, intraday_df: pd.DataFrame, selection: List[SelectionPlan]) -> pd.DataFrame:
        symbols = {plan.symbol for plan in selection}
        df = intraday_df[intraday_df["symbol"].isin(symbols)].copy()
        df = df[(df["timestamp"] >= self.sim_start) & (df["timestamp"] <= self.sim_end)]
        df.sort_values(["symbol", "timestamp"], inplace=True)
        df["ret_1"] = df.groupby("symbol")["close"].pct_change().fillna(0)
        df["ret_5"] = df.groupby("symbol")["close"].pct_change(5).fillna(0)
        df["vol_20"] = (
            df.groupby("symbol")["ret_1"].rolling(20).std().reset_index(level=0, drop=True).bfill().fillna(1e-4)
        )
        df["score"] = ((df["ret_5"] / (df["vol_20"] + 1e-6)) + 0.1 * df["ret_1"]).clip(-3, 3)
        df["future_return"] = df.groupby("symbol")["close"].pct_change(-5).fillna(0)
        return df

    def _simulate(
        self,
        score_df: pd.DataFrame,
        selection: List[SelectionPlan],
        overrides: Optional[Dict[str, float]] = None,
        include_grid: bool = True,
    ) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, object], Dict[str, object]]:
        plans = {plan.symbol: plan for plan in selection}
        if score_df.empty:
            raise RuntimeError("No intraday data for selected tickers in window")
        trades: List[dict] = []
        open_positions: Dict[str, dict] = {}
        capital_in_use = 0.0
        turnover = 0.0
        slippage_records: List[dict] = []
        overrides = overrides or {}
        entry_threshold = overrides.get("entry_threshold", self.cfg.entry_threshold)
        exit_threshold = overrides.get("exit_threshold", self.cfg.exit_threshold)
        target_pct = overrides.get("target_pct", self.cfg.target_pct)
        stop_pct = overrides.get("stop_pct", self.cfg.stop_pct)
        max_holding = int(overrides.get("max_holding_minutes", self.cfg.max_holding_minutes))
        ret_std = float(score_df["ret_1"].std()) if not score_df["ret_1"].empty else float("nan")
        base_vol_trigger = ret_std * 3 if not math.isnan(ret_std) else None
        volatility_trigger = overrides.get("volatility_trigger", base_vol_trigger)

        def calc_fees(notional: float) -> float:
            commission = max(self.cfg.min_brokerage, self.cfg.commission_pct * notional)
            statutory = (self.cfg.gst_pct + self.cfg.exchange_fees_pct) * notional
            return commission + statutory

        idx = 0
        for row in score_df.itertuples():
            plan = plans.get(row.symbol)
            if not plan:
                continue
            spread_pct = float(getattr(row, "spread_pct", self.cfg.slippage_mean))
            score = float(row.score)
            price = float(row.close)
            if price <= 0:
                continue
            position = open_positions.get(row.symbol)
            if position is None:
                if score <= entry_threshold:
                    continue
                if plan.liquidity_score < self.cfg.shortlist_liquidity_buffer:
                    continue
                if spread_pct > self.cfg.max_spread_pct:
                    continue
                notional = plan.quantity * price
                if capital_in_use + notional > self.cfg.max_total_invest:
                    continue
                entry_slippage = float(
                    np.clip(self.rng.normal(self.cfg.slippage_mean, self.cfg.slippage_sd), -0.003, 0.003)
                )
                exec_price = price * (1 + entry_slippage)
                fees = calc_fees(notional)
                turnover += notional
                open_positions[row.symbol] = {
                    "entry_ts": row.timestamp,
                    "entry_price": exec_price,
                    "qty": plan.quantity,
                    "notional": notional,
                    "entry_score": score,
                    "fees_entry": fees,
                    "entry_slippage": entry_slippage,
                }
                capital_in_use += notional
            else:
                elapsed_minutes = (row.timestamp - position["entry_ts"]).total_seconds() / 60
                pnl_pct = (price - position["entry_price"]) / position["entry_price"]
                exit_reason = None
                if pnl_pct >= target_pct:
                    exit_reason = "target"
                elif pnl_pct <= -stop_pct:
                    exit_reason = "stop"
                elif score < exit_threshold:
                    exit_reason = "signal"
                elif elapsed_minutes >= max_holding:
                    exit_reason = "time"
                elif (
                    volatility_trigger is not None
                    and not math.isnan(volatility_trigger)
                    and abs(row.ret_1) > volatility_trigger
                ):
                    exit_reason = "volatility"

                if exit_reason:
                    exit_slippage = float(
                        np.clip(self.rng.normal(self.cfg.slippage_mean / 2, self.cfg.slippage_sd), -0.003, 0.003)
                    )
                    exec_price = price * (1 - exit_slippage)
                    gross = (exec_price - position["entry_price"]) * position["qty"]
                    exit_notional = exec_price * position["qty"]
                    fees_exit = calc_fees(exit_notional)
                    net = gross - (position["fees_entry"] + fees_exit)
                    capital_in_use -= position["notional"]
                    trade_id = f"{row.symbol}-{idx}"
                    idx += 1
                    trade_record = {
                        "trade_id": trade_id,
                        "ticker": row.symbol,
                        "side": "LONG",
                        "qty": position["qty"],
                        "entry_timestamp": position["entry_ts"].isoformat(),
                        "exit_timestamp": row.timestamp.isoformat(),
                        "entry_price": round(position["entry_price"], 4),
                        "exit_price": round(exec_price, 4),
                        "fees": round(position["fees_entry"] + fees_exit, 2),
                        "gross_pnl": round(gross, 2),
                        "net_pnl": round(net, 2),
                        "return_pct": round(gross / max(position["entry_price"] * position["qty"], 1e-9), 6),
                        "holding_minutes": round(elapsed_minutes, 2),
                        "exit_reason": exit_reason,
                        "entry_signal": position["entry_score"],
                        "exit_signal": score,
                        "slippage_bps_entry": round(position["entry_slippage"] * 10_000, 2),
                        "slippage_bps_exit": round(exit_slippage * 10_000, 2),
                    }
                    trades.append(trade_record)
                    slippage_records.append(
                        {
                            "trade_id": trade_id,
                            "symbol": row.symbol,
                            "entry_bps": trade_record["slippage_bps_entry"],
                            "exit_bps": trade_record["slippage_bps_exit"],
                        }
                    )
                    turnover += exit_notional
                    del open_positions[row.symbol]

        for symbol, position in list(open_positions.items()):
            last_rows = score_df[score_df["symbol"] == symbol].tail(1)
            if last_rows.empty:
                continue
            row = last_rows.iloc[0]
            exit_price = row["close"]
            exit_slippage = float(np.clip(self.rng.normal(self.cfg.slippage_mean / 2, self.cfg.slippage_sd), -0.003, 0.003))
            exec_price = exit_price * (1 - exit_slippage)
            gross = (exec_price - position["entry_price"]) * position["qty"]
            fees_exit = calc_fees(exec_price * position["qty"])
            net = gross - (position["fees_entry"] + fees_exit)
            trade_id = f"{symbol}-{idx}"
            trades.append(
                {
                    "trade_id": trade_id,
                    "ticker": symbol,
                    "side": "LONG",
                    "qty": position["qty"],
                    "entry_timestamp": position["entry_ts"].isoformat(),
                    "exit_timestamp": row["timestamp"].isoformat(),
                    "entry_price": round(position["entry_price"], 4),
                    "exit_price": round(exec_price, 4),
                    "fees": round(position["fees_entry"] + fees_exit, 2),
                    "gross_pnl": round(gross, 2),
                    "net_pnl": round(net, 2),
                    "return_pct": round(gross / max(position["entry_price"] * position["qty"], 1e-9), 6),
                    "holding_minutes": round(
                        (row["timestamp"] - position["entry_ts"]).total_seconds() / 60,
                        2,
                    ),
                    "exit_reason": "forced",
                    "entry_signal": position["entry_score"],
                    "exit_signal": row["score"],
                    "slippage_bps_entry": round(position["entry_slippage"] * 10_000, 2),
                    "slippage_bps_exit": round(exit_slippage * 10_000, 2),
                }
            )
            del open_positions[symbol]

        trades_df = pd.DataFrame(trades)
        equity_curve_df = self._build_equity_curve(trades_df)
        portfolio_metrics = self._compute_portfolio_metrics(trades_df, equity_curve_df, turnover)
        diagnostics = self._build_diagnostics(score_df, trades_df, slippage_records)
        if include_grid:
            portfolio_metrics["grid_search"] = self._parameter_grid(score_df, selection)
        return trades_df, equity_curve_df, portfolio_metrics, diagnostics

    def _build_equity_curve(self, trades_df: pd.DataFrame) -> pd.DataFrame:
        if trades_df.empty:
            return pd.DataFrame(columns=["timestamp", "cash", "positions", "nav"])
        trades_df = trades_df.sort_values("exit_timestamp")
        base_capital = self.cfg.max_total_invest
        cash = 0.0
        records = []
        for _, trade in trades_df.iterrows():
            cash += trade["net_pnl"]
            records.append(
                {
                    "timestamp": trade["exit_timestamp"],
                    "cash": round(cash, 2),
                    "positions": 0.0,
                    "nav": round(base_capital + cash, 2),
                }
            )
        return pd.DataFrame(records)

    def _compute_portfolio_metrics(
        self, trades_df: pd.DataFrame, equity_curve: pd.DataFrame, turnover: float
    ) -> Dict[str, object]:
        gross_pnl = float(trades_df["gross_pnl"].sum()) if not trades_df.empty else 0.0
        net_pnl = float(trades_df["net_pnl"].sum()) if not trades_df.empty else 0.0
        roic = net_pnl / self.cfg.max_total_invest if self.cfg.max_total_invest else 0.0
        win_rate = (
            float((trades_df["net_pnl"] > 0).mean()) if not trades_df.empty else 0.0
        )
        avg_pnl = float(trades_df["net_pnl"].mean()) if not trades_df.empty else 0.0
        max_dd = (
            float((equity_curve["nav"] / self.cfg.max_total_invest - 1).min())
            if not equity_curve.empty
            else 0.0
        )
        duration_stats = {
            "mean_minutes": float(trades_df["holding_minutes"].mean()) if not trades_df.empty else 0.0,
            "median_minutes": float(trades_df["holding_minutes"].median()) if not trades_df.empty else 0.0,
        }
        turnover_ratio = turnover / self.cfg.max_total_invest if self.cfg.max_total_invest else 0.0
        returns_series = (
            trades_df.set_index("exit_timestamp")["net_pnl"] / self.cfg.max_total_invest
            if not trades_df.empty
            else pd.Series(dtype=float)
        )
        metrics = compute_metrics(returns_series)
        downside = returns_series[returns_series < 0]
        sortino = (
            returns_series.mean() / (downside.std(ddof=0) + 1e-9) * np.sqrt(252)
            if not downside.empty
            else 0.0
        )
        return {
            "gross_pnl": gross_pnl,
            "net_pnl": net_pnl,
            "roic": roic,
            "win_rate": win_rate,
            "avg_pnl": avg_pnl,
            "max_drawdown": max_dd,
            "duration": duration_stats,
            "turnover": turnover_ratio,
            "annualized_return": metrics.get("cagr", 0.0),
            "volatility": returns_series.std(ddof=0) if not returns_series.empty else 0.0,
            "sharpe": metrics.get("sharpe", 0.0),
            "sortino": sortino,
            "trade_count": int(len(trades_df)),
        }

    def _build_diagnostics(
        self,
        score_df: pd.DataFrame,
        trades_df: pd.DataFrame,
        slippage_records: List[dict],
    ) -> Dict[str, object]:
        feature_distribution = {
            "score_mean": float(score_df["score"].mean()),
            "score_std": float(score_df["score"].std()),
            "score_p05": float(score_df["score"].quantile(0.05)),
            "score_p95": float(score_df["score"].quantile(0.95)),
        }
        ic_series = (
            score_df.groupby(pd.Grouper(key="timestamp", freq="1D"))
            .apply(lambda df: df["score"].corr(df["future_return"]), include_groups=False)
            .dropna()
        )
        stability = {
            "mean_ic": float(ic_series.mean()) if not ic_series.empty else 0.0,
            "median_ic": float(ic_series.median()) if not ic_series.empty else 0.0,
        }
        slippage_df = pd.DataFrame(slippage_records)
        largest_slippage = (
            slippage_df.assign(total_bps=lambda d: d["entry_bps"].abs() + d["exit_bps"].abs())
            .sort_values("total_bps", ascending=False)
            .head(5)
            .to_dict(orient="records")
            if not slippage_df.empty
            else []
        )
        adverse_trades = pd.DataFrame()
        if not trades_df.empty:
            pnl_std = trades_df["net_pnl"].std()
            if pnl_std and not math.isnan(pnl_std) and pnl_std > 0:
                adverse_trades = trades_df[trades_df["net_pnl"] < -3 * pnl_std]
        return {
            "feature_distribution": feature_distribution,
            "stability": stability,
            "largest_slippage_events": largest_slippage,
            "adverse_trades": adverse_trades.to_dict(orient="records"),
        }

    def _parameter_grid(self, score_df: pd.DataFrame, selection: List[SelectionPlan]) -> List[Dict[str, object]]:
        grid_cases = [
            {"entry_threshold": self.cfg.entry_threshold - 0.1, "stop_pct": self.cfg.stop_pct * 0.8},
            {"entry_threshold": self.cfg.entry_threshold, "stop_pct": self.cfg.stop_pct},
            {"entry_threshold": self.cfg.entry_threshold + 0.1, "stop_pct": self.cfg.stop_pct * 1.2},
        ]
        summaries: List[Dict[str, object]] = []
        base_state = deepcopy(self.rng.bit_generator.state)
        for case in grid_cases:
            self.rng.bit_generator.state = deepcopy(base_state)
            overrides = {
                "entry_threshold": case["entry_threshold"],
                "stop_pct": case["stop_pct"],
                "exit_threshold": self.cfg.exit_threshold,
                "target_pct": self.cfg.target_pct,
            }
            trades_df, _, metrics, _ = self._simulate(
                score_df.copy(), selection, overrides=overrides, include_grid=False
            )
            summaries.append(
                {
                    "entry_threshold": case["entry_threshold"],
                    "stop_pct": case["stop_pct"],
                    "sharpe": metrics.get("sharpe", 0.0),
                    "win_rate": metrics.get("win_rate", 0.0),
                    "trade_count": metrics.get("trade_count", 0),
                }
            )
        self.rng.bit_generator.state = base_state
        return summaries

    # ------------------------------------------------------------------
    # Artifact writing
    # ------------------------------------------------------------------
    def _write_artifacts(
        self,
        shortlist_df: pd.DataFrame,
        selection: List[SelectionPlan],
        trades_df: pd.DataFrame,
        equity_curve_df: pd.DataFrame,
        portfolio_metrics: Dict[str, object],
        diagnostics: Dict[str, object],
        manifest_path: Path,
    ) -> Dict[str, str]:
        date_code = self.cfg.run_date
        shortlist_path = self.artifact_dir / f"shortlist_{date_code}.csv"
        selection_path = self.artifact_dir / f"selection_{date_code}.json"
        trades_path = self.artifact_dir / f"trades_{date_code}.csv"
        backtest_report_path = self.artifact_dir / f"backtest_report_{date_code}.json"
        equity_curve_path = self.artifact_dir / f"equity_curve_{date_code}.csv"
        diagnostics_path = self.artifact_dir / f"diagnostics_{date_code}.json"
        debug_log_path = self.artifact_dir / f"debug_{date_code}.log"

        shortlist_df.to_csv(shortlist_path, index=False)
        selection_payload = {
            "selection_mode": self.cfg.selection_mode,
            "max_total_invest": self.cfg.max_total_invest,
            "run_date": date_code,
            "tickers": [
                {
                    "symbol": plan.symbol,
                    "quantity": plan.quantity,
                    "lot_size": plan.lot_size,
                    "entry_price": plan.entry_price,
                    "position_value": plan.position_value,
                    "liquidity_score": plan.liquidity_score,
                    "volatility_score": plan.volatility_score,
                    "momentum_score": plan.momentum_score,
                    "stability_score": plan.stability_score,
                }
                for plan in selection
            ],
        }
        selection_path.write_text(json.dumps(selection_payload, indent=2))

        trades_df.to_csv(trades_path, index=False)
        if not equity_curve_df.empty:
            equity_curve_df.to_csv(equity_curve_path, index=False)
        else:
            equity_curve_path.write_text("timestamp,cash,positions,nav\n")

        backtest_report = {
            "run_date": date_code,
            "params": asdict(self.cfg),
            "portfolio_metrics": portfolio_metrics,
            "trades_path": str(trades_path),
            "equity_curve_path": str(equity_curve_path),
            "manifest_path": str(manifest_path),
        }
        backtest_report_path.write_text(json.dumps(backtest_report, indent=2, default=str))

        diagnostics_path.write_text(json.dumps(diagnostics, indent=2, default=str))

        debug_log = [
            f"Random seed: {self.cfg.random_seed}",
            f"Sim window (UTC): {self.sim_start} → {self.sim_end}",
            f"Selection mode: {self.cfg.selection_mode}",
            f"Selected tickers: {[plan.symbol for plan in selection]}",
            f"Trades generated: {len(trades_df)}",
        ]
        debug_log_path.write_text("\n".join(debug_log))

        return {
            "manifest": str(manifest_path),
            "shortlist": str(shortlist_path),
            "selection": str(selection_path),
            "trades": str(trades_path),
            "backtest_report": str(backtest_report_path),
            "equity_curve": str(equity_curve_path),
            "diagnostics": str(diagnostics_path),
            "debug_log": str(debug_log_path),
        }

    def _write_error(self, filename: str, payload: Dict[str, object]) -> None:
        path = self.artifact_dir / filename
        path.write_text(json.dumps(payload, indent=2))
