from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class MarketBar(BaseModel):
    source: str = Field(default="kite")
    symbol: str
    instrument_token: Optional[int] = None
    interval: str = Field(default="1m")
    start_ts: datetime
    end_ts: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    oi: Optional[float] = Field(default=None, description="Open interest for derivatives")
    ingest_ts: datetime
