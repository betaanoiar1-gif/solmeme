"""
Confidence Score Calculator (0 to 100).
Measures data completeness, wallet sample depth, liquidity stability,
and verified real-trade sample depth. Unknown fields remain penalized.
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

        # Confidence budget: 35 holders + 25 liquidity + 20 history + 20 verified trades.
        # A higher verified-trade sample increases confidence without changing alpha/risk.
        if holders is not None:
            holder_confidence = min((holders / 1_000.0) * 35.0, 35.0)
        else:
            holder_confidence = 8.75  # Unknown penalty

        if liquidity is not None:
            liquidity_confidence = min((liquidity / 50_000.0) * 25.0, 25.0)
        else:
            liquidity_confidence = 4.0  # Unknown penalty

        history_confidence = min((dna_snapshots_count / 10.0) * 20.0, 20.0)

        # trades_count is the number of real parsed swaps observed for this token.
        # It is deliberately capped so a very large sample cannot dominate confidence.
        verified_trade_confidence = min((max(trades_count, 0) / 100.0) * 20.0, 20.0)

        confidence = (
            holder_confidence
            + liquidity_confidence
            + history_confidence
            + verified_trade_confidence
        )
        return round(min(max(confidence, 15.0), 100.0), 2)
