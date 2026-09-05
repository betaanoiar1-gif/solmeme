"""
Sniper Mode E: Hybrid Multi-Factor Sniper.
Combines early launch, smart money backing, whale accumulation, and momentum.
"""

from scoring.opportunity.opportunity_scorer import OpportunityReport


class HybridSniper:
    @classmethod
    def evaluate(
        cls,
        opp: OpportunityReport,
        smart_money_score: float,
        whale_netflow: float,
        is_pre_ignition: bool
    ) -> bool:
        triggers_met = 0
        if opp.alpha_score >= 75.0:
            triggers_met += 1
        if smart_money_score >= 75.0:
            triggers_met += 1
        if whale_netflow > 10_000.0:
            triggers_met += 1
        if is_pre_ignition or opp.earlyness_score >= 65.0:
            triggers_met += 1

        return triggers_met >= 3 and opp.risk_score <= 40.0 and opp.recommendation == "PAPER_ENTRY"
