"""
Virtual Wallet and Strict Accounting Engine.
Guarantees mathematical accounting invariants:
Equity = Cash + Net Liquidation Value
Ending Equity = Starting Capital + Realized PnL + Net Unrealized PnL
"""

from dataclasses import dataclass, field
import time
from typing import Any, Dict, List, Optional, Tuple
import uuid

from blockchain.solana.types import Provenance, SourceType
from simulation.execution.execution_engine import SimulatedExecutionResult


@dataclass
class VirtualPosition:
    position_id: str
    mint: str
    symbol: str
    entry_time: float
    entry_price: float
    size_usd: float  # Capital invested
    tokens_amount: float
    current_price: float
    current_gross_value_usd: float
    estimated_liquidation_value_usd: float  # After exit fees & slippage
    unrealized_pnl_usd: float
    unrealized_pnl_pct: float
    peak_price: float
    lowest_price: float
    entry_fees_paid_usd: float
    entry_slippage_paid_usd: float
    alpha_score: float
    risk_score: float
    regime: str
    provenance: Provenance = field(default_factory=Provenance)
    is_open: bool = True

    @property
    def current_value_usd(self) -> float:
        """Backwards compatibility alias for current_gross_value_usd."""
        return self.current_gross_value_usd


class VirtualWallet:
    def __init__(self, name: str = "VirtualWallet", initial_capital_usd: float = 100.0, data_mode: str = "live"):
        self.name = name
        self.initial_capital_usd = round(float(initial_capital_usd), 4)
        self.cash_usd = round(float(initial_capital_usd), 4)
        self.realized_pnl_usd = 0.0
        self.total_entry_fees_usd = 0.0
        self.total_exit_fees_usd = 0.0
        self.total_slippage_usd = 0.0
        self.peak_equity = float(initial_capital_usd)
        self.max_drawdown_pct = 0.0
        self.data_mode = data_mode

        self.positions: Dict[str, VirtualPosition] = {}
        self.closed_positions_history: List[VirtualPosition] = []

    @property
    def total_fees_usd(self) -> float:
        return self.total_entry_fees_usd + self.total_exit_fees_usd

    @property
    def open_positions_gross_value_usd(self) -> float:
        return sum(pos.current_gross_value_usd for pos in self.positions.values() if pos.is_open)

    @property
    def open_positions_net_liquidation_value_usd(self) -> float:
        return sum(pos.estimated_liquidation_value_usd for pos in self.positions.values() if pos.is_open)

    @property
    def total_unrealized_pnl_usd(self) -> float:
        return sum(pos.unrealized_pnl_usd for pos in self.positions.values() if pos.is_open)

    @property
    def equity_usd(self) -> float:
        """Fundamental invariant: Equity = Cash + Net Liquidation Value of Open Positions."""
        return round(self.cash_usd + self.open_positions_net_liquidation_value_usd, 4)

    def validate_accounting_invariants(self) -> Tuple[bool, str]:
        """
        Verify:
        1. equity == cash + net_liquidation_value
        2. equity == starting_capital + realized_pnl + net_unrealized_pnl
        """
        calc_equity_1 = round(self.cash_usd + self.open_positions_net_liquidation_value_usd, 2)
        calc_equity_2 = round(self.initial_capital_usd + self.realized_pnl_usd + self.total_unrealized_pnl_usd, 2)
        curr_equity = round(self.equity_usd, 2)

        diff_1 = abs(calc_equity_1 - curr_equity)
        diff_2 = abs(calc_equity_2 - curr_equity)

        if diff_1 > 0.02 or diff_2 > 0.02:
            msg = (
                f"ACCOUNTING INVARIANT VIOLATION: Current Equity=${curr_equity:.2f}, "
                f"Cash+LiqValue=${calc_equity_1:.2f} (diff: {diff_1:.4f}), "
                f"Capital+Realized+Unrealized=${calc_equity_2:.2f} (diff: {diff_2:.4f})"
            )
            return False, msg

        return True, "INVARIANTS_SATISFIED"

    def update_prices(self, price_map: Dict[str, float], fee_rate: float = 0.0025, base_slippage_rate: float = 0.005):
        """Update mark-to-market valuations and estimated liquidation values."""
        for mint, pos in self.positions.items():
            if pos.is_open and mint in price_map:
                curr_p = price_map[mint]
                pos.current_price = curr_p
                gross_val = pos.tokens_amount * curr_p
                pos.current_gross_value_usd = gross_val

                # Estimated liquidation value after exit DEX fees & slippage
                estimated_exit_cost = gross_val * (fee_rate + base_slippage_rate) + 0.015
                net_liq_val = max(gross_val - estimated_exit_cost, 0.0)
                pos.estimated_liquidation_value_usd = net_liq_val

                # Net unrealized PnL = Net liquidation value - Total cost basis (size + entry fees)
                total_cost_basis = pos.size_usd + pos.entry_fees_paid_usd
                pos.unrealized_pnl_usd = round(net_liq_val - total_cost_basis, 4)
                pos.unrealized_pnl_pct = round((pos.unrealized_pnl_usd / max(total_cost_basis, 1e-9)) * 100.0, 2)

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
        regime: str = "R3_EARLY_IGNITION",
        provenance: Optional[Provenance] = None
    ) -> Optional[VirtualPosition]:
        # Cost to buy: size + entry fees
        invested_capital = exec_res.filled_size_usd
        entry_fee = exec_res.fees.total_fee_usd
        total_deduction = invested_capital + entry_fee

        if total_deduction > self.cash_usd:
            return None  # Insufficient cash

        self.cash_usd = round(self.cash_usd - total_deduction, 4)
        self.total_entry_fees_usd = round(self.total_entry_fees_usd + entry_fee, 4)
        self.total_slippage_usd = round(self.total_slippage_usd + exec_res.slippage.slippage_usd, 4)

        gross_val = invested_capital
        # Liquidation value immediately accounts for entry fee & exit friction drag
        net_liq_val = max(invested_capital - (invested_capital * 0.0075) - 0.015, 0.0)
        total_cost_basis = invested_capital + entry_fee

        pos = VirtualPosition(
            position_id=str(uuid.uuid4())[:8],
            mint=mint,
            symbol=symbol,
            entry_time=time.time(),
            entry_price=exec_res.executed_price,
            size_usd=invested_capital,
            tokens_amount=exec_res.tokens_amount,
            current_price=exec_res.executed_price,
            current_gross_value_usd=gross_val,
            estimated_liquidation_value_usd=net_liq_val,
            unrealized_pnl_usd=round(net_liq_val - total_cost_basis, 4),
            unrealized_pnl_pct=round(((net_liq_val - total_cost_basis) / max(total_cost_basis, 1e-9)) * 100.0, 2),
            peak_price=exec_res.executed_price,
            lowest_price=exec_res.executed_price,
            entry_fees_paid_usd=entry_fee,
            entry_slippage_paid_usd=exec_res.slippage.slippage_usd,
            alpha_score=alpha_score,
            risk_score=risk_score,
            regime=regime,
            provenance=provenance or Provenance(
                source_type=SourceType.REAL if self.data_mode == "live" else SourceType.MOCK,
                provider="VirtualWalletSimulator"
            ),
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

        # Proceeds from sell: Gross filled size - exit fees
        gross_proceeds = exec_res.filled_size_usd
        exit_fee = exec_res.fees.total_fee_usd
        net_proceeds = round(gross_proceeds - exit_fee, 4)

        self.cash_usd = round(self.cash_usd + net_proceeds, 4)
        self.total_exit_fees_usd = round(self.total_exit_fees_usd + exit_fee, 4)
        self.total_slippage_usd = round(self.total_slippage_usd + exec_res.slippage.slippage_usd, 4)

        # Net Realized PnL = Net Proceeds Received - Capital Invested - Entry Fees Paid
        trade_realized_pnl = round(net_proceeds - pos.size_usd - pos.entry_fees_paid_usd, 4)
        self.realized_pnl_usd = round(self.realized_pnl_usd + trade_realized_pnl, 4)

        pos.is_open = False
        pos.current_price = exec_res.executed_price
        pos.current_gross_value_usd = 0.0
        pos.estimated_liquidation_value_usd = 0.0
        pos.unrealized_pnl_usd = 0.0
        pos.unrealized_pnl_pct = 0.0

        self.closed_positions_history.append(pos)
        del self.positions[mint]
        return pos

    def get_summary(self) -> Dict[str, Any]:
        is_valid, inv_msg = self.validate_accounting_invariants()
        return {
            "name": self.name,
            "data_mode": self.data_mode,
            "initial_capital": round(self.initial_capital_usd, 2),
            "equity": round(self.equity_usd, 2),
            "cash": round(self.cash_usd, 2),
            "open_positions_gross_val": round(self.open_positions_gross_value_usd, 2),
            "open_positions_val": round(self.open_positions_net_liquidation_value_usd, 2),
            "realized_pnl": round(self.realized_pnl_usd, 2),
            "unrealized_pnl": round(self.total_unrealized_pnl_usd, 2),
            "total_fees": round(self.total_fees_usd, 2),
            "total_slippage": round(self.total_slippage_usd, 2),
            "max_drawdown_pct": round(self.max_drawdown_pct, 2),
            "open_positions_count": len(self.positions),
            "closed_trades_count": len(self.closed_positions_history),
            "accounting_invariant_valid": is_valid,
            "accounting_status": inv_msg
        }
