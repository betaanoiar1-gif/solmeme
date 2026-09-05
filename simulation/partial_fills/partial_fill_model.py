"""
Partial Fill Simulation Model.
Calculates filled quantity, unfilled quantity, and fill ratio.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class FillResult:
    requested_size_usd: float
    filled_size_usd: float
    unfilled_size_usd: float
    fill_ratio: float  # 0.0 to 1.0


class PartialFillModel:
    @classmethod
    def calculate(cls, requested_usd: float, liquidity_usd: Optional[float] = None, enable_partial: bool = True) -> FillResult:
        if not enable_partial or liquidity_usd is None:
            # When liquidity is unknown, do not fabricate synthetic pool depth
            return FillResult(
                requested_size_usd=round(requested_usd, 2),
                filled_size_usd=round(requested_usd, 2),
                unfilled_size_usd=0.0,
                fill_ratio=1.0
            )

        # If trade size is > 5% of entire pool, it only fills partially
        max_fill_capacity = max(liquidity_usd * 0.05, 10.0)
        if requested_usd > max_fill_capacity:
            filled = max_fill_capacity
            unfilled = requested_usd - filled
            ratio = filled / requested_usd
        else:
            filled = requested_usd
            unfilled = 0.0
            ratio = 1.0

        return FillResult(
            requested_size_usd=round(requested_usd, 2),
            filled_size_usd=round(filled, 2),
            unfilled_size_usd=round(unfilled, 2),
            fill_ratio=round(ratio, 4)
        )
