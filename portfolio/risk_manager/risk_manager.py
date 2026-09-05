"""
Portfolio Risk Management and Circuit Breakers.
Protects virtual capital against consecutive loss streaks and market-wide drawdowns.
"""

from dataclasses import dataclass
from typing import List
from app.config.settings import PortfolioConfig


@dataclass
class RiskCheckResult:
    allowed_to_trade: bool
    is_circuit_breaker_active: bool
    reason: str


class PortfolioRiskManager:
    def __init__(self, config: PortfolioConfig):
        self.config = config
        self._consecutive_losses = 0
        self._daily_starting_equity = config.initial_capital_usd

    def register_trade_outcome(self, is_win: bool):
        if is_win:
            self._consecutive_losses = 0
        else:
            self._consecutive_losses += 1

    def evaluate_risk(
        self,
        current_equity: float,
        current_cash: float,
        max_drawdown_pct: float
    ) -> RiskCheckResult:
        # 1. Consecutive loss breaker
        if self._consecutive_losses >= self.config.consecutive_loss_breaker_count:
            return RiskCheckResult(
                allowed_to_trade=False,
                is_circuit_breaker_active=True,
                reason=f"CIRCUIT BREAKER: {self._consecutive_losses} consecutive losses reached"
            )

        # 2. Max Drawdown breaker
        if max_drawdown_pct >= self.config.max_drawdown_limit_percent:
            return RiskCheckResult(
                allowed_to_trade=False,
                is_circuit_breaker_active=True,
                reason=f"CIRCUIT BREAKER: Max drawdown ({max_drawdown_pct:.1f}%) exceeds limit ({self.config.max_drawdown_limit_percent:.1f}%)"
            )

        # 3. Daily loss breaker
        daily_loss_pct = ((self._daily_starting_equity - current_equity) / max(self._daily_starting_equity, 1.0)) * 100.0
        if daily_loss_pct >= self.config.max_daily_loss_percent:
            return RiskCheckResult(
                allowed_to_trade=False,
                is_circuit_breaker_active=True,
                reason=f"CIRCUIT BREAKER: Daily loss ({daily_loss_pct:.1f}%) exceeds limit ({self.config.max_daily_loss_percent:.1f}%)"
            )

        return RiskCheckResult(allowed_to_trade=True, is_circuit_breaker_active=False, reason="RISK_NORMAL")
