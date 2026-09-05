"""
Confidence Score Calculator (0 to 100).
Measures data completeness, wallet sample depth, and liquidity stability.
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
        holders = int(token_data.get("holders_count", 0))
        liquidity = float(token_data.get("liquidity", 0.0))

        # Sample depth scores
        holder_confidence = min((holders / 1_000.0) * 40.0, 40.0)
        history_confidence = min((dna_snapshots_count / 10.0) * 30.0, 30.0)
        liquidity_confidence = min((liquidity / 50_000.0) * 30.0, 30.0)

        confidence = holder_confidence + history_confidence + liquidity_confidence
        return round(min(max(confidence, 15.0), 100.0), 2)
