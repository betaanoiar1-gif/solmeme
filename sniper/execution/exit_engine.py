"""
Dynamic Exit Engine.
Evaluates multi-tier Take Profit, Stop Loss, Trailing Stops,
Smart Money dump exits, Regime transition breakdowns, and
stateful loss-of-thesis protection.
"""

from dataclasses import dataclass
import time
from typing import Dict, Optional

from app.config.settings import ExitConfig


@dataclass
class ExitVerdict:
    should_exit: bool
    sell_ratio: float
    exit_reason: str
    is_stop_loss: bool


class DynamicExitEngine:
    def __init__(self, config: Optional[ExitConfig] = None):
        self.config = config or ExitConfig()
        # Keyed by entry identity so a temporary one-cycle drawdown does not
        # immediately close a position. Breaches must persist for the configured
        # number of observations.
        self._soft_loss_breach_counts: Dict[str, int] = {}

    @staticmethod
    def _position_key(entry_price: float, entry_time: float) -> str:
        return f"{entry_price:.16g}:{entry_time:.6f}"

    def _soft_loss_confirmed(
        self,
        entry_price: float,
        entry_time: float,
        pnl_pct: float,
        current_time: float,
    ) -> bool:
        key = self._position_key(entry_price, entry_time)
        hold_minutes = max(0.0, (current_time - entry_time) / 60.0)

        if hold_minutes < self.config.soft_loss_min_hold_minutes:
            self._soft_loss_breach_counts.pop(key, None)
            return False

        if pnl_pct > -self.config.soft_loss_exit_percent:
            self._soft_loss_breach_counts.pop(key, None)
            return False

        count = self._soft_loss_breach_counts.get(key, 0) + 1
        self._soft_loss_breach_counts[key] = count
        return count >= max(1, int(self.config.soft_loss_confirmations))

    def _clear_position_state(self, entry_price: float, entry_time: float) -> None:
        self._soft_loss_breach_counts.pop(self._position_key(entry_price, entry_time), None)

    def evaluate_position(
        self,
        entry_price: float,
        current_price: float,
        peak_price: float,
        entry_time: float,
        current_time: float,
        smart_money_score: float,
        whale_netflow: float,
        regime: str,
        liquidity_usd: Optional[float] = None,
    ) -> ExitVerdict:
        pnl_pct = ((current_price - entry_price) / max(entry_price, 1e-9)) * 100.0
        peak_gain_pct = ((peak_price - entry_price) / max(entry_price, 1e-9)) * 100.0
        duration_minutes = (current_time - entry_time) / 60.0

        # 0. Liquidity Drain / Rug Exit. UNKNOWN liquidity never becomes a
        # synthetic zero, so absence of data cannot manufacture an exit.
        if liquidity_usd is not None and self.config.exit_on_liquidity_drain and liquidity_usd < 500.0:
            self._clear_position_state(entry_price, entry_time)
            return ExitVerdict(True, 1.0, f"LIQUIDITY_DRAIN_DETECTED (Liquidity ${liquidity_usd:.1f} < $500.0)", True)

        # 1. Hard stop remains the final unconditional loss boundary.
        if pnl_pct <= -self.config.stop_loss_percent:
            self._clear_position_state(entry_price, entry_time)
            return ExitVerdict(True, 1.0, f"STOP_LOSS_TRIGGERED ({pnl_pct:.1f}% <= -{self.config.stop_loss_percent:.1f}%)", True)

        # 2. Stateful soft loss protection. This is a capital-preservation
        # mechanism, not a prediction: a losing position must remain below the
        # threshold across multiple live observations before it is closed.
        if self._soft_loss_confirmed(entry_price, entry_time, pnl_pct, current_time):
            self._clear_position_state(entry_price, entry_time)
            return ExitVerdict(
                True,
                1.0,
                f"THESIS_LOSS_CONFIRMED ({pnl_pct:.1f}% <= -{self.config.soft_loss_exit_percent:.1f}% for {self.config.soft_loss_confirmations} observations)",
                True,
            )

        # 3. Trailing stop protects a meaningful winner from a violent reversal.
        if peak_gain_pct >= self.config.trailing_stop_activation_percent:
            drawdown_from_peak_pct = ((peak_price - current_price) / max(peak_price, 1e-9)) * 100.0
            if drawdown_from_peak_pct >= self.config.trailing_stop_distance_percent:
                self._clear_position_state(entry_price, entry_time)
                return ExitVerdict(
                    True,
                    1.0,
                    f"TRAILING_STOP_TRIGGERED (Peak +{peak_gain_pct:.1f}%, Pullback -{drawdown_from_peak_pct:.1f}%)",
                    False,
                )

        # 4. Take-profit tiers.
        if pnl_pct >= self.config.take_profit_target_3_percent:
            self._clear_position_state(entry_price, entry_time)
            return ExitVerdict(True, 1.0, f"TAKE_PROFIT_TIER_3 (+{pnl_pct:.1f}% target hit)", False)

        if pnl_pct >= self.config.take_profit_target_2_percent:
            self._clear_position_state(entry_price, entry_time)
            return ExitVerdict(True, self.config.take_profit_target_2_sell_ratio, f"TAKE_PROFIT_TIER_2 (+{pnl_pct:.1f}% target hit)", False)

        if pnl_pct >= self.config.take_profit_target_1_percent:
            self._clear_position_state(entry_price, entry_time)
            return ExitVerdict(True, self.config.take_profit_target_1_sell_ratio, f"TAKE_PROFIT_TIER_1 (+{pnl_pct:.1f}% target hit)", False)

        # 5. Independent flow deterioration.
        if self.config.exit_on_smart_money_dump and smart_money_score < 30.0 and whale_netflow < -25_000.0:
            self._clear_position_state(entry_price, entry_time)
            return ExitVerdict(True, 1.0, "SMART_MONEY_DUMP_DETECTED (Whale net selling)", False)

        # 6. Current regime failure. The engine intentionally consumes the
        # caller's current regime rather than inventing a new regime itself.
        if regime in ("R8_DISTRIBUTION", "R9_COLLAPSE"):
            self._clear_position_state(entry_price, entry_time)
            return ExitVerdict(True, 1.0, f"REGIME_BREAKDOWN ({regime})", False)

        # 7. Time decay: an unchanged or weak thesis eventually releases capital.
        if duration_minutes > self.config.max_holding_time_minutes and pnl_pct < 5.0:
            self._clear_position_state(entry_price, entry_time)
            return ExitVerdict(True, 1.0, f"MAX_HOLDING_TIME_EXPIRED ({duration_minutes:.0f}m)", False)

        return ExitVerdict(False, 0.0, "HOLD", False)
