"""
Sniper Mode A: Early Launch Sniper.
Targets freshly deployed tokens (< 2 hours) with locked LP and revoked authorities.
"""

from typing import Dict, Any, Optional
from scoring.opportunity.opportunity_scorer import OpportunityReport


class EarlyLaunchSniper:
    @classmethod
    def evaluate(cls, opp: OpportunityReport, age_minutes: Optional[float]) -> bool:
        if age_minutes is None:
            return False
        return (
            opp.recommendation == "PAPER_ENTRY" and
            opp.alpha_score >= 68.0 and
            opp.risk_score <= 40.0 and
            age_minutes <= 120.0 and
            opp.earlyness_score >= 70.0
        )
