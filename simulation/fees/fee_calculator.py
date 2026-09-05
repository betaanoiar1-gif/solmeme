"""
Fee Calculator for Solana DEX and network fees.
"""

from dataclasses import dataclass
from app.config.settings import ExecutionConfig


@dataclass
class TransactionFeeBreakdown:
    dex_lp_fee_usd: float
    solana_base_fee_usd: float
    priority_fee_usd: float
    total_fee_usd: float


class FeeCalculator:
    @classmethod
    def calculate(cls, trade_size_usd: float, config: ExecutionConfig) -> TransactionFeeBreakdown:
        dex_lp_fee = trade_size_usd * (config.simulated_dex_fee_percent / 100.0)
        base_fee = config.simulated_solana_base_fee_usd
        priority_fee = config.simulated_priority_fee_usd
        total = dex_lp_fee + base_fee + priority_fee

        return TransactionFeeBreakdown(
            dex_lp_fee_usd=round(dex_lp_fee, 4),
            solana_base_fee_usd=round(base_fee, 4),
            priority_fee_usd=round(priority_fee, 4),
            total_fee_usd=round(total, 4)
        )
