"""
Chase Detector.
Separates Token Quality from Entry Quality to prevent buying parabolic tops.
"""

from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class EntryQualityVerdict:
    is_safe_entry: bool
    is_chasing: bool
    entry_score: float  # 0 to 100
    action: str  # "EXECUTE_NOW", "WAIT_FOR_RETEST", "DO_NOT_ENTER"
    reason: str


class ChaseDetector:
    @classmethod
    def evaluate_entry(
        cls,
        price_velocity: float,
        price_acceleration: float,
        regime: str,
        alpha_score: float
    ) -> EntryQualityVerdict:
        # If token is in Euphoria or Extreme Parabolic with high velocity
        if regime in ("R6_PARABOLIC", "R7_EUPHORIA") and price_velocity > 0.40:
            return EntryQualityVerdict(
                is_safe_entry=False,
                is_chasing=True,
                entry_score=30.0,
                action="WAIT_FOR_RETEST",
                reason="GOOD TOKEN, BAD ENTRY (Parabolic top / High chase risk; Wait for retest)"
            )

        if regime == "R8_DISTRIBUTION" or regime == "R9_COLLAPSE":
            return EntryQualityVerdict(
                is_safe_entry=False,
                is_chasing=False,
                entry_score=10.0,
                action="DO_NOT_ENTER",
                reason="Distribution/Collapse regime in progress"
            )

        if alpha_score >= 70.0 and regime in ("R2_ACCUMULATION", "R3_EARLY_IGNITION", "R4_CONFIRMED_IGNITION"):
            return EntryQualityVerdict(
                is_safe_entry=True,
                is_chasing=False,
                entry_score=90.0,
                action="EXECUTE_NOW",
                reason="Optimal entry window during early ignition/accumulation"
            )

        return EntryQualityVerdict(
            is_safe_entry=True,
            is_chasing=False,
            entry_score=70.0,
            action="EXECUTE_NOW",
            reason="Standard entry conditions met"
        )
