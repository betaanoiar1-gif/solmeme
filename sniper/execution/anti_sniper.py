"""
Anti-Sniper and Manipulation Defense Engine.
Detects bot sandwiching, artificial volume, bundled launches, and spoofed liquidity.
"""

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class AntiSniperVerdict:
    is_manipulated: bool
    risk_level: str  # "LOW", "MEDIUM", "CRITICAL"
    defense_triggers: List[str]


class AntiSniperDefense:
    @classmethod
    def evaluate(
        cls,
        sec_data: Dict[str, Any],
        cluster_discount: float,
        insider_prob: float,
        is_wash_traded: bool
    ) -> AntiSniperVerdict:
        triggers = []
        is_manipulated = False

        if is_wash_traded:
            triggers.append("Wash-trading bots generating circular volume")
            is_manipulated = True

        if cluster_discount < 0.40:
            triggers.append(f"Severe wallet bundling detected (Cluster discount: {cluster_discount:.2f})")
            is_manipulated = True

        if insider_prob > 60.0:
            triggers.append(f"High insider-like coordination ({insider_prob:.1f}%)")
            is_manipulated = True

        if is_manipulated:
            risk = "CRITICAL"
        elif cluster_discount < 0.70 or insider_prob > 35.0:
            risk = "MEDIUM"
        else:
            risk = "LOW"

        return AntiSniperVerdict(
            is_manipulated=is_manipulated,
            risk_level=risk,
            defense_triggers=triggers
        )
