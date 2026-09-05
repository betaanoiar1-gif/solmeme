"""
Sniper Mode C: Whale Radar Sniper.
Enters alongside high-confidence whale accumulation.
"""

from scoring.opportunity.opportunity_scorer import OpportunityReport


class WhaleSniper:
    @classmethod
    def evaluate(cls, opp: OpportunityReport, whale_netflow: float) -> bool:
        return (
            opp.recommendation in ("PAPER_ENTRY", "WATCH") and
            whale_netflow >= 20_000.0 and
            opp.alpha_score >= 65.0 and
            opp.risk_score <= 45.0
        )
