"""
Sniper Mode B: Smart Money Follow Sniper.
Triggers on verified smart money wallet accumulation with positive netflow.
"""

from scoring.opportunity.opportunity_scorer import OpportunityReport


class SmartMoneySniper:
    @classmethod
    def evaluate(cls, opp: OpportunityReport, smart_money_score: float, netflow_usd: float) -> bool:
        return (
            opp.recommendation in ("PAPER_ENTRY", "WATCH") and
            smart_money_score >= 78.0 and
            netflow_usd > 5_000.0 and
            opp.risk_score <= 45.0
        )
