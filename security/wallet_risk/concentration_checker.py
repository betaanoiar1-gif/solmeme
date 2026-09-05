"""
Holder and Creator Concentration Checker.
Detects insider bundling, top-10 concentration skew, and dev dump risk.
"""

from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class ConcentrationCheckResult:
    top10_holder_pct: float
    dev_holding_pct: float
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

        top10 = float(sec_data.get("top10_holder_pct", 20.0))
        dev_holding = float(sec_data.get("dev_holding_pct", 0.0))

        if top10 > max_top10_pct:
            excess = top10 - max_top10_pct
            risk_points += (excess / (100.0 - max_top10_pct)) * 40.0
            reasons.append(f"Top 10 holders control {top10:.1f}% (> {max_top10_pct:.1f}% limit)")

        if dev_holding > max_dev_pct:
            excess_dev = dev_holding - max_dev_pct
            risk_points += (excess_dev / (100.0 - max_dev_pct)) * 50.0
            reasons.append(f"Creator/Dev wallet holds {dev_holding:.1f}% (> {max_dev_pct:.1f}% limit; High dump risk)")

        is_acceptable = (top10 <= max_top10_pct and dev_holding <= max_dev_pct)
        return ConcentrationCheckResult(
            top10_holder_pct=top10,
            dev_holding_pct=dev_holding,
            is_acceptable=is_acceptable,
            risk_points=min(risk_points, 100.0),
            reasons=reasons
        )
