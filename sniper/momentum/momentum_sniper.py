"""
Sniper Mode D: Momentum & Pre-Ignition Sniper.
Triggers on microstructural acceleration before parabolic breakout.
"""

from scoring.opportunity.opportunity_scorer import OpportunityReport


class MomentumSniper:
    @classmethod
    def evaluate(cls, opp: OpportunityReport, is_pre_ignition: bool, price_velocity: float) -> bool:
        return (
            (opp.recommendation == "PAPER_ENTRY" or is_pre_ignition) and
            opp.alpha_score >= 70.0 and
            price_velocity > 0.01 and
            price_velocity < 0.35 and  # Not chasing top
            opp.risk_score <= 45.0
        )
