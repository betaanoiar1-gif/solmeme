"""
Unified Simulated Order Execution Engine.
Calculates realistic executed price, slippage, DEX & network fees,
partial fills, and execution latency.
"""

from dataclasses import dataclass
import time
from typing import Optional

from app.config.settings import ExecutionConfig
from simulation.fees.fee_calculator import FeeCalculator, TransactionFeeBreakdown
from simulation.latency.latency_simulator import LatencyProfile, LatencySimulator
from simulation.partial_fills.partial_fill_model import FillResult, PartialFillModel
from simulation.slippage.slippage_model import SlippageModel, SlippageResult


@dataclass
class SimulatedExecutionResult:
    is_buy: bool
    requested_size_usd: float
    filled_size_usd: float
    unfilled_size_usd: float
    fill_ratio: float
    market_price: float
    executed_price: float
    tokens_amount: float
    slippage: SlippageResult
    fees: TransactionFeeBreakdown
    latency: LatencyProfile
    total_cost_usd: float
    timestamp: float


class ExecutionSimulator:
    def __init__(self, config: Optional[ExecutionConfig] = None):
        self.config = config or ExecutionConfig()

    def execute_order(
        self,
        market_price: float,
        trade_size_usd: float,
        liquidity_usd: Optional[float] = None,
        is_buy: bool = True,
        latency_mode: str = "fast"
    ) -> SimulatedExecutionResult:
        # 1. Partial fill calculation
        fill_res = PartialFillModel.calculate(
            requested_usd=trade_size_usd,
            liquidity_usd=liquidity_usd,
            enable_partial=self.config.enable_partial_fills
        )

        active_size_usd = fill_res.filled_size_usd

        # 2. Latency simulation
        latency_profile = LatencySimulator.simulate(mode=latency_mode, base_ms=self.config.default_latency_ms)

        # 3. Slippage & Price Impact calculation
        slippage_res = SlippageModel.calculate(
            market_price=market_price * (1.0 + latency_profile.slippage_drift_factor),
            trade_size_usd=active_size_usd,
            liquidity_usd=liquidity_usd,
            is_buy=is_buy,
            config=self.config
        )

        # 4. Fee calculation
        fee_breakdown = FeeCalculator.calculate(
            trade_size_usd=active_size_usd,
            config=self.config
        )

        # 5. Tokens amount
        exec_price = slippage_res.executed_price
        tokens_amt = active_size_usd / max(exec_price, 1e-12)

        # Total cost
        if is_buy:
            total_cost = active_size_usd + fee_breakdown.total_fee_usd
        else:
            total_cost = active_size_usd - fee_breakdown.total_fee_usd

        return SimulatedExecutionResult(
            is_buy=is_buy,
            requested_size_usd=fill_res.requested_size_usd,
            filled_size_usd=fill_res.filled_size_usd,
            unfilled_size_usd=fill_res.unfilled_size_usd,
            fill_ratio=fill_res.fill_ratio,
            market_price=market_price,
            executed_price=exec_price,
            tokens_amount=tokens_amt,
            slippage=slippage_res,
            fees=fee_breakdown,
            latency=latency_profile,
            total_cost_usd=round(total_cost, 4),
            timestamp=time.time()
        )
