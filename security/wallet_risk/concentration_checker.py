"""
Holder and Creator Concentration Checker.
Detects insider bundling, top-10 concentration skew, and dev dump risk.
Preserves UNKNOWN (None) semantics without guessing default percentages.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class ConcentrationCheckResult:
    top10_holder_pct: Optional[float]
    dev_holding_pct: Optional[float]
    is_acceptable: bool
    risk_points: float
    reasons: list


class ConcentrationChecker:
    @classmethod
    def check(
        cls,
        sec_data: Dict[str, Any],
        max_top10_pct: float = 65.0,
        max_dev_pct: float = 15.0
    ) -> ConcentrationCheckResult:
        reasons = []
        risk_points = 0.0
        acceptable = True

        raw_top10 = sec_data.get("top10_holder_pct")
        if raw_top10 is not None:
            top10 = float(raw_top10)
            if top10 > max_top10_pct:
                excess = top10 - max_top10_pct
                risk_points += (excess / (100.0 - max_top10_pct)) * 40.0
                reasons.append(f"Top 10 holders control {top10:.1f}% (> {max_top10_pct:.1f}% limit)")
                acceptable = False
        else:
            top10 = None
            risk_points += 20.0
            reasons.append("Top 10 holder distribution UNKNOWN")
            acceptable = False

        raw_dev = sec_data.get("dev_holding_pct")
        if raw_dev is not None:
            dev_holding = float(raw_dev)
            if dev_holding > max_dev_pct:
                excess_dev = dev_holding - max_dev_pct
                risk_points += (excess_dev / (100.0 - max_dev_pct)) * 50.0
                reasons.append(f"Creator/Dev wallet holds {dev_holding:.1f}% (> {max_dev_pct:.1f}% limit; High dump risk)")
                acceptable = False
        else:
            dev_holding = None
            risk_points += 15.0
            reasons.append("Creator/Dev holding percentage UNKNOWN")
            acceptable = False

        return ConcentrationCheckResult(
            top10_holder_pct=top10,
            dev_holding_pct=dev_holding,
            is_acceptable=acceptable,
            risk_points=min(risk_points, 100.0),
            reasons=reasons
        )
