from __future__ import annotations

from datetime import datetime
from typing import Dict, Iterable, Optional

import numpy as np
import pandas as pd

from quant_india.common import get_settings
from quant_india.common.time import ist_now
from quant_india.data.loaders.base import BackfillMixin, BaseIngestionJob
from quant_india.data.writer import write_partitioned

try:
    from kiteconnect import KiteConnect
except ImportError:  # pragma: no cover - kiteconnect is optional
    KiteConnect = None  # type: ignore[assignment]


PLACEHOLDER_TOKEN = "<<"


class KiteHistoricalIngestion(BaseIngestionJob, BackfillMixin):
    def __init__(self, session: Optional[KiteConnect] = None):
        super().__init__(source="kite")
        self.settings = get_settings()
        self.session = session or self._build_session()

    def _build_session(self) -> Optional[KiteConnect]:
        if KiteConnect is None:
            return None
        kite_config = self.settings.data_sources.kite
        if any(PLACEHOLDER_TOKEN in value for value in [kite_config.api_key, kite_config.access_token]):
            return None
        session = KiteConnect(api_key=kite_config.api_key)
        session.set_access_token(kite_config.access_token)
        return session

    def _use_live_api(self) -> bool:
        return self.session is not None

    def fetch(
        self,
        symbols: Iterable[str],
        start: datetime,
        end: datetime,
        interval: str = "1m",
        instrument_tokens: Optional[Dict[str, int]] = None,
        continuous: bool = False,
        oi: bool = True,
        **_: dict,
    ) -> pd.DataFrame:
        frames = []
        for symbol in symbols:
            if self._use_live_api():
                if not instrument_tokens or symbol not in instrument_tokens:
                    raise ValueError(f"Instrument token required for symbol {symbol}")
                data = self.session.historical_data(  # type: ignore[union-attr]
                    instrument_token=instrument_tokens[symbol],
                    from_date=pd.Timestamp(start, tz="Asia/Kolkata").to_pydatetime(),
                    to_date=pd.Timestamp(end, tz="Asia/Kolkata").to_pydatetime(),
                    interval=interval,
                    continuous=continuous,
                    oi=oi,
                )
                df = pd.DataFrame(data)
                if df.empty:
                    continue
                df["timestamp"] = pd.to_datetime(df["date"], utc=True)
                df = df.drop(columns=["date"])
                df["symbol"] = symbol
            else:
                df = self._simulate(symbol=symbol, start=start, end=end, interval=interval)
            frames.append(df)

        if not frames:
            return pd.DataFrame()

        result = pd.concat(frames, ignore_index=True)
        result["source"] = self.source
        result["interval"] = interval
        result["ingest_ts"] = ist_now().tz_convert("UTC")
        return result

    def _simulate(self, symbol: str, start: datetime, end: datetime, interval: str) -> pd.DataFrame:
        freq_map = {"1m": "1min", "5m": "5min", "15m": "15min"}
        freq = freq_map.get(interval, "1min")
        idx = pd.date_range(start=start, end=end, freq=freq, tz="Asia/Kolkata", inclusive="left")
        if len(idx) == 0:
            return pd.DataFrame()
        prices = 100 + np.cumsum(np.random.normal(0, 0.1, size=len(idx)))
        highs = prices + np.abs(np.random.normal(0, 0.05, size=len(idx)))
        lows = prices - np.abs(np.random.normal(0, 0.05, size=len(idx)))
        opens = prices + np.random.normal(0, 0.02, size=len(idx))
        closes = prices + np.random.normal(0, 0.02, size=len(idx))
        volume = np.random.randint(1_000, 50_000, size=len(idx))

        df = pd.DataFrame(
            {
                "timestamp": idx.tz_convert("UTC"),
                "open": opens,
                "high": highs,
                "low": lows,
                "close": closes,
                "volume": volume,
                "oi": np.nan,
                "symbol": symbol,
            }
        )
        return df

    def write(self, df: pd.DataFrame) -> None:
        df = df.copy()
        df["date"] = df["timestamp"].dt.tz_convert("Asia/Kolkata").dt.strftime("%Y-%m-%d")
        write_partitioned(
            df,
            root=self.settings.storage.raw_root / f"source={self.source}",
            partition_cols=["date", "symbol"],
        )
