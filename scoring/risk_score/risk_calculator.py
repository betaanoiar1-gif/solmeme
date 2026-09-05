"""
Multi-Factor Risk Score Calculator (0 to 100).
Lower is safer. Blends rug probability, concentration, liquidity depth, and manipulation.
Preserves UNKNOWN (None) semantics without guessing default liquidity.
"""

from typing import Optional
from security.rug_detection.rug_engine import SecurityEvaluation
from intelligence.market_microstructure.microstructure import MicrostructureMetrics


class RiskCalculator:
    @classmethod
    def calculate(
        cls,
        security_eval: SecurityEvaluation,
        micro: MicrostructureMetrics,
        liquidity_usd: Optional[float] = None
    ) -> float:
        # Base risk from security engine
        base_risk = security_eval.rug_probability

        # Liquidity thinness penalty (Conservative penalty for UNKNOWN depth)
        if liquidity_usd is None:
            liq_penalty = 25.0  # Conservative unknown penalty
        elif liquidity_usd < 5_000.0:
            liq_penalty = 30.0
        elif liquidity_usd < 25_000.0:
            liq_penalty = 15.0
        elif liquidity_usd < 100_000.0:
            liq_penalty = 5.0
        else:
            liq_penalty = 0.0

        # Fake breakout or manipulation penalty
        manipulation_penalty = 40.0 if micro.is_fake_breakout else 0.0

        total_risk = base_risk * 0.60 + liq_penalty * 0.20 + manipulation_penalty * 0.20
        return round(min(max(total_risk, 0.0), 100.0), 2)
