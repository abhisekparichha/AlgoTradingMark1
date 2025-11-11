from __future__ import annotations

import uuid
from datetime import datetime
from typing import List

from quant_india.executor.orders import OrderRequest, OrderResponse


class SimulatedExecutor:
    def __init__(self):
        self.orders: List[OrderResponse] = []

    def place_order(self, request: OrderRequest) -> OrderResponse:
        response = OrderResponse(
            order_id=f"SIM-{uuid.uuid4().hex[:10]}",
            status="FILLED",
            message="Simulated execution",
            timestamp=datetime.utcnow(),
        )
        self.orders.append(response)
        return response
