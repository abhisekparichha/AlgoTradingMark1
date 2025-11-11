from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CostModel:
    brokerage_pct: float = 0.0003
    stamp_duty_pct: float = 0.00015
    exchange_charges_pct: float = 0.00002
    slippage_factor: float = 0.5  # proportion of spread paid

    def transaction_cost(self, notional: float, spread: float) -> float:
        brokerage = self.brokerage_pct * notional
        stamp_duty = self.stamp_duty_pct * notional
        exchange = self.exchange_charges_pct * notional
        slippage = self.slippage_factor * spread
        return brokerage + stamp_duty + exchange + slippage
