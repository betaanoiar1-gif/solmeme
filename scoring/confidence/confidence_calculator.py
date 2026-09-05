"""
Confidence Score Calculator (0 to 100).
Measures data completeness, wallet sample depth, and liquidity stability.
Penalizes confidence when market features are UNKNOWN (None).
"""

from typing import Any, Dict


class ConfidenceCalculator:
    @classmethod
    def calculate(
        cls,
        token_data: Dict[str, Any],
        dna_snapshots_count: int,
        trades_count: int
    ) -> float:
        raw_holders = token_data.get("holders_count")
        holders = int(raw_holders) if raw_holders is not None else None
        raw_liq = token_data.get("liquidity")
        liquidity = float(raw_liq) if raw_liq is not None else None

        # Sample depth scores
        if holders is not None:
            holder_confidence = min((holders / 1_000.0) * 40.0, 40.0)
        else:
            holder_confidence = 10.0  # Unknown penalty

        if liquidity is not None:
            liquidity_confidence = min((liquidity / 50_000.0) * 30.0, 30.0)
        else:
            liquidity_confidence = 5.0  # Unknown penalty

        history_confidence = min((dna_snapshots_count / 10.0) * 30.0, 30.0)

        confidence = holder_confidence + history_confidence + liquidity_confidence
        return round(min(max(confidence, 15.0), 100.0), 2)
