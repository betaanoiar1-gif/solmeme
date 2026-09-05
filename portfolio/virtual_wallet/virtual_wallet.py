"""
Virtual Wallet.
Simulates a self-contained paper trading wallet starting at $100.00 USD.
Zero private keys, zero real money.
"""

from dataclasses import dataclass, field
import time
from typing import Dict, List, Optional
import uuid

from app.config.settings import PortfolioConfig
from simulation.execution.execution_engine import SimulatedExecutionResult


@dataclass
class VirtualPosition:
    position_id: str
    mint: str
    symbol: str
    entry_time: float
    entry_price: float
    size_usd: float
    tokens_amount: float
    current_price: float
    current_value_usd: float
    unrealized_pnl_usd: float
    unrealized_pnl_pct: float
    peak_price: float
    lowest_price: float
    fees_paid_usd: float
    slippage_paid_usd: float
    alpha_score: float
    risk_score: float
    regime: str
    is_open: bool = True


class VirtualWallet:
    def __init__(self, name: str = "VirtualWallet", initial_capital_usd: float = 100.0):
        self.name = name
        self.initial_capital_usd = float(initial_capital_usd)
        self.cash_usd = float(initial_capital_usd)
        self.realized_pnl_usd = 0.0
        self.total_fees_usd = 0.0
        self.total_slippage_usd = 0.0
        self.peak_equity = float(initial_capital_usd)
        self.max_drawdown_pct = 0.0

        self.positions: Dict[str, VirtualPosition] = {}  # mint -> VirtualPosition
        self.closed_positions_history: List[VirtualPosition] = []

    @property
    def open_positions_value_usd(self) -> float:
        return sum(pos.current_value_usd for pos in self.positions.values() if pos.is_open)

    @property
    def total_unrealized_pnl_usd(self) -> float:
        return sum(pos.unrealized_pnl_usd for pos in self.positions.values() if pos.is_open)

    @property
    def equity_usd(self) -> float:
        return self.cash_usd + self.open_positions_value_usd

    def update_prices(self, price_map: Dict[str, float]):
        """Update current prices and recalculate mark-to-market positions."""
        for mint, pos in self.positions.items():
            if pos.is_open and mint in price_map:
                curr_p = price_map[mint]
                pos.current_price = curr_p
                pos.current_value_usd = pos.tokens_amount * curr_p
                pos.unrealized_pnl_usd = pos.current_value_usd - pos.size_usd
                pos.unrealized_pnl_pct = (pos.unrealized_pnl_usd / max(pos.size_usd, 1e-9)) * 100.0

                if curr_p > pos.peak_price:
                    pos.peak_price = curr_p
                if curr_p < pos.lowest_price:
                    pos.lowest_price = curr_p

        # Update drawdown
        current_eq = self.equity_usd
        if current_eq > self.peak_equity:
            self.peak_equity = current_eq
        dd = ((self.peak_equity - current_eq) / max(self.peak_equity, 1e-9)) * 100.0
        if dd > self.max_drawdown_pct:
            self.max_drawdown_pct = dd

    def open_position(
        self,
        mint: str,
        symbol: str,
        exec_res: SimulatedExecutionResult,
        alpha_score: float = 75.0,
        risk_score: float = 20.0,
        regime: str = "R3_EARLY_IGNITION"
    ) -> Optional[VirtualPosition]:
        cost = exec_res.total_cost_usd
        if cost > self.cash_usd:
            return None  # Insufficient cash

        self.cash_usd -= cost
        self.total_fees_usd += exec_res.fees.total_fee_usd
        self.total_slippage_usd += exec_res.slippage.slippage_usd

        pos = VirtualPosition(
            position_id=str(uuid.uuid4())[:8],
            mint=mint,
            symbol=symbol,
            entry_time=time.time(),
            entry_price=exec_res.executed_price,
            size_usd=exec_res.filled_size_usd,
            tokens_amount=exec_res.tokens_amount,
            current_price=exec_res.executed_price,
            current_value_usd=exec_res.filled_size_usd,
            unrealized_pnl_usd=0.0,
            unrealized_pnl_pct=0.0,
            peak_price=exec_res.executed_price,
            lowest_price=exec_res.executed_price,
            fees_paid_usd=exec_res.fees.total_fee_usd,
            slippage_paid_usd=exec_res.slippage.slippage_usd,
            alpha_score=alpha_score,
            risk_score=risk_score,
            regime=regime,
            is_open=True
        )

        self.positions[mint] = pos
        return pos

    def close_position(
        self,
        mint: str,
        exec_res: SimulatedExecutionResult,
        exit_reason: str = "TAKE_PROFIT"
    ) -> Optional[VirtualPosition]:
        pos = self.positions.get(mint)
        if not pos or not pos.is_open:
            return None

        proceeds = exec_res.total_cost_usd  # for sell, total_cost_usd is size - fees
        self.cash_usd += proceeds
        self.total_fees_usd += exec_res.fees.total_fee_usd
        self.total_slippage_usd += exec_res.slippage.slippage_usd

        # Realized PnL after entry fees and exit fees
        trade_realized_pnl = proceeds - pos.size_usd - pos.fees_paid_usd
        self.realized_pnl_usd += trade_realized_pnl

        pos.is_open = False
        pos.current_price = exec_res.executed_price
        pos.current_value_usd = 0.0
        pos.unrealized_pnl_usd = 0.0
        pos.unrealized_pnl_pct = 0.0

        self.closed_positions_history.append(pos)
        del self.positions[mint]
        return pos

    def get_summary(self) -> Dict[str, any]:
        return {
            "name": self.name,
            "initial_capital": round(self.initial_capital_usd, 2),
            "equity": round(self.equity_usd, 2),
            "cash": round(self.cash_usd, 2),
            "open_positions_val": round(self.open_positions_value_usd, 2),
            "realized_pnl": round(self.realized_pnl_usd, 2),
            "unrealized_pnl": round(self.total_unrealized_pnl_usd, 2),
            "total_fees": round(self.total_fees_usd, 2),
            "total_slippage": round(self.total_slippage_usd, 2),
            "max_drawdown_pct": round(self.max_drawdown_pct, 2),
            "open_positions_count": len(self.positions),
            "closed_trades_count": len(self.closed_positions_history)
        }
