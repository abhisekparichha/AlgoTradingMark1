from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from loguru import logger

from quant_india.common import get_settings
from quant_india.executor.orders import OrderRequest, OrderResponse

try:
    from kiteconnect import KiteConnect
except ImportError:  # pragma: no cover
    KiteConnect = None  # type: ignore


@dataclass
class KiteSession:
    client: Optional[KiteConnect] = None


class ZerodhaExecutor:
    def __init__(self, dry_run: bool = True, confirm_live: bool = False, session: Optional[KiteConnect] = None):
        self.settings = get_settings()
        self.dry_run = dry_run
        self.confirm_live = confirm_live
        if not self.dry_run and not self.confirm_live:
            raise ValueError("Live trading requires --confirm-live flag")
        self.session = session or self._create_session()

    def _create_session(self) -> Optional[KiteConnect]:
        if KiteConnect is None:
            logger.warning("kiteconnect package not installed; executor running in dry mode")
            return None
        kite_config = self.settings.data_sources.kite
        if any("<<" in value for value in [kite_config.api_key, kite_config.access_token]):
            logger.warning("Kite API credentials not configured; executor running in dry mode")
            return None
        client = KiteConnect(api_key=kite_config.api_key)
        client.set_access_token(kite_config.access_token)
        return client

    def place_order(self, request: OrderRequest) -> OrderResponse:
        logger.info("Placing order: {}", request)
        if self.dry_run or self.session is None:
            order_id = f"SIM-{uuid.uuid4().hex[:10]}"
            return OrderResponse(order_id=order_id, status="SIMULATED", message="Dry run order", timestamp=datetime.utcnow())
        params = {
            "tradingsymbol": request.symbol,
            "quantity": request.quantity,
            "exchange": "NSE",
            "transaction_type": request.transaction_type,
            "order_type": request.order_type,
            "product": request.product,
        }
        if request.price:
            params["price"] = request.price
        if request.trigger_price:
            params["trigger_price"] = request.trigger_price
        if request.tag:
            params["tag"] = request.tag
        order_id = self.session.place_order(**params)  # type: ignore[union-attr]
        return OrderResponse(order_id=order_id, status="OPEN", message="Order placed", timestamp=datetime.utcnow())
