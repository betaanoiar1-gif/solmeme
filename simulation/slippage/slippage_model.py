"""
Slippage and Price Impact Model for AMMs (Raydium / Orca / Pump.fun).
"""

from dataclasses import dataclass
from typing import Optional
from app.config.settings import ExecutionConfig


@dataclass
class SlippageResult:
    base_slippage_pct: float
    price_impact_pct: float
    total_slippage_pct: float
    slippage_usd: float
    executed_price: float


class SlippageModel:
    @classmethod
    def calculate(
        cls,
        market_price: float,
        trade_size_usd: float,
        liquidity_usd: Optional[float],
        is_buy: bool,
        config: ExecutionConfig
    ) -> SlippageResult:
        base_slip = config.base_slippage_percent

        # AMM Constant product price impact: I = (size / liquidity) * constant
        # If liquidity is unknown (None), apply conservative minimum depth
        effective_liq = max(liquidity_usd, 1_000.0) if liquidity_usd is not None else 5_000.0
        impact = (trade_size_usd / effective_liq) * config.liquidity_impact_constant * 100.0
        total_slip_pct = base_slip + impact

        slippage_usd = trade_size_usd * (total_slip_pct / 100.0)

        if is_buy:
            # Slippage pushes BUY price higher
            executed_price = market_price * (1.0 + (total_slip_pct / 100.0))
        else:
            # Slippage pushes SELL price lower
            executed_price = market_price * (1.0 - (total_slip_pct / 100.0))

        return SlippageResult(
            base_slippage_pct=round(base_slip, 3),
            price_impact_pct=round(impact, 3),
            total_slippage_pct=round(total_slip_pct, 3),
            slippage_usd=round(slippage_usd, 4),
            executed_price=executed_price
        )
