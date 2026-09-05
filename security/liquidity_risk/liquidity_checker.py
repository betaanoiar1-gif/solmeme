"""
Liquidity Risk and LP Status Checker.
Checks pool liquidity depth, LP lock/burn percentage, and removable liquidity danger.
Preserves UNKNOWN (None) semantics without guessing default percentages.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class LiquidityCheckResult:
    lp_locked_pct: Optional[float]
    is_locked_adequate: bool
    risk_points: float
    reasons: list


class LiquidityRiskChecker:
    @classmethod
    def check(cls, sec_data: Dict[str, Any], min_lp_locked_pct: float = 70.0) -> LiquidityCheckResult:
        reasons = []
        risk_points = 0.0

        raw_locked = sec_data.get("lp_locked_pct")
        if raw_locked is not None:
            lp_locked_pct = float(raw_locked)
            if lp_locked_pct < min_lp_locked_pct:
                deficit = min_lp_locked_pct - lp_locked_pct
                risk_points += (deficit / min_lp_locked_pct) * 60.0
                reasons.append(f"LP Lock is {lp_locked_pct:.1f}% (< {min_lp_locked_pct:.1f}% required; Dev can pull liquidity)")
                is_locked_adequate = False
            else:
                is_locked_adequate = True
        else:
            lp_locked_pct = None
            risk_points += 40.0
            reasons.append("LP Lock status UNKNOWN (cannot verify locked liquidity depth)")
            is_locked_adequate = False

        return LiquidityCheckResult(
            lp_locked_pct=lp_locked_pct,
            is_locked_adequate=is_locked_adequate,
            risk_points=min(risk_points, 100.0),
            reasons=reasons
        )
