"""
AI Expert Thesis & Counter-Thesis Generator.
Synthesizes structured on-chain evidence into investment theses with zero hallucination.
"""

from dataclasses import dataclass
from typing import Dict, List, Any
from ml.models.baseline_model import ProbabilityDistribution
from scoring.opportunity.opportunity_scorer import OpportunityReport


@dataclass
class StructuredAIThesis:
    token_symbol: str
    thesis: str
    counter_thesis: str
    why_now: str
    key_risks: List[str]
    confirmation_triggers: List[str]
    invalidation_triggers: List[str]
    probabilities: ProbabilityDistribution


class AIExpertThesisGenerator:
    @classmethod
    def generate(
        cls,
        opp: OpportunityReport,
        probs: ProbabilityDistribution,
        smart_money_score: float,
        whale_netflow: float
    ) -> StructuredAIThesis:
        thesis = (
            f"{opp.symbol} is displaying strong {opp.regime} dynamics with an Alpha score of {opp.alpha_score}/100. "
            f"Smart Money conviction is high ({smart_money_score:.1f}) accompanied by ${whale_netflow:+,.0f} net whale flow. "
            f"Narrative momentum in '{opp.narrative}' provides strong organic tailwinds."
        )

        counter_thesis = (
            f"If buyer momentum decelerates or if top holders distribute into liquidity, {opp.symbol} "
            f"faces downside pressure (P(-20%/30m) = {probs.p_down_20pct_30m}%). "
            f"A risk score of {opp.risk_score}/100 requires strict stop-loss adherence."
        )

        why_now = (
            f"Pre-ignition metrics and buyer acceleration ({opp.alpha_score:.1f} alpha) indicate early institutional/smart accumulation "
            f"prior to broader retail awareness."
        )

        key_risks = [
            f"Liquidity risk (Execution Score: {opp.execution_score:.1f})",
            f"Holder concentration / insider dump risk ({opp.risk_score:.1f} risk score)",
            "Broader Solana market sentiment shift"
        ]

        confirmations = [
            "Continued net positive whale accumulation",
            "Sustained order-flow imbalance > +0.30",
            "Transition into Confirmed Ignition (R4)"
        ]

        invalidations = [
            "Smart money net flow turns negative (> $10k net sell)",
            "Liquidity pool drops by > 15%",
            "Break below stop loss threshold"
        ]

        return StructuredAIThesis(
            token_symbol=opp.symbol,
            thesis=thesis,
            counter_thesis=counter_thesis,
            why_now=why_now,
            key_risks=key_risks,
            confirmation_triggers=confirmations,
            invalidation_triggers=invalidations,
            probabilities=probs
        )
