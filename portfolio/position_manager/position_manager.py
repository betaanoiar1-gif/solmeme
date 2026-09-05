"""
Dynamic Position Sizing Engine.
Sizes positions dynamically based on Alpha, Risk, Liquidity depth, and Portfolio Heat.
Preserves UNKNOWN (None) semantics: if liquidity is None or <= 0, size is 0.0 (entry blocked).
"""

from typing import Optional
from app.config.settings import PortfolioConfig
from scoring.opportunity.opportunity_scorer import OpportunityReport


class PositionManager:
    def __init__(self, config: PortfolioConfig):
        self.config = config

    def calculate_position_size(
        self,
        opp: OpportunityReport,
        current_cash: float,
        current_equity: float,
        open_positions_count: int,
        pool_liquidity_usd: Optional[float] = None
    ) -> float:
        # Check capacity
        if open_positions_count >= self.config.max_open_positions:
            return 0.0

        if current_cash < self.config.min_position_size_usd:
            return 0.0

        # When pool liquidity is UNKNOWN or non-positive, block position sizing
        if pool_liquidity_usd is None or pool_liquidity_usd <= 0:
            return 0.0

        # Base size: 15% of equity
        base_size = current_equity * 0.15

        # Factor adjustments
        alpha_multiplier = opp.alpha_score / 100.0
        risk_discount = (100.0 - opp.risk_score) / 100.0
        confidence_multiplier = opp.confidence_score / 100.0

        adjusted_size = base_size * (0.5 + alpha_multiplier * 0.5) * risk_discount * confidence_multiplier

        # Hard constraints
        adjusted_size = min(adjusted_size, self.config.max_position_size_usd)
        adjusted_size = min(adjusted_size, current_cash * 0.90)  # Reserve 10% cash buffer
        adjusted_size = min(adjusted_size, pool_liquidity_usd * 0.02)  # Never exceed 2% of total pool

        if adjusted_size < self.config.min_position_size_usd:
            return 0.0

        return round(adjusted_size, 2)
