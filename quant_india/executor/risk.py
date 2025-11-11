from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RiskLimits:
    max_position: int = 1000
    max_notional: float = 10_000_000.0
    max_drawdown_pct: float = 0.15


class RiskManager:
    def __init__(self, limits: RiskLimits):
        self.limits = limits

    def validate_order(self, symbol: str, quantity: int, price: float) -> None:
        notional = abs(quantity) * price
        if abs(quantity) > self.limits.max_position:
            raise ValueError(f"Quantity {quantity} exceeds max position {self.limits.max_position}")
        if notional > self.limits.max_notional:
            raise ValueError(f"Notional {notional} exceeds max {self.limits.max_notional}")
