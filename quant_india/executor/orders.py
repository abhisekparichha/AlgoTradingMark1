from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class OrderRequest:
    symbol: str
    quantity: int
    order_type: str = "MARKET"
    transaction_type: str = "BUY"
    product: str = "MIS"
    price: Optional[float] = None
    trigger_price: Optional[float] = None
    tag: Optional[str] = None


@dataclass
class OrderResponse:
    order_id: str
    status: str
    message: str
    timestamp: datetime
