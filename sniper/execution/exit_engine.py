"""
Dynamic Exit Engine.
Evaluates multi-tier Take Profit, Stop Loss, Trailing Stops,
Smart Money dump exits, and Regime transition breakdowns.
"""

from dataclasses import dataclass
import time
from typing import Dict, Any, Optional
from app.config.settings import ExitConfig


@dataclass
class ExitVerdict:
    should_exit: bool
    sell_ratio: float  # 0.0 to 1.0 (1.0 = full close, 0.5 = partial close)
    exit_reason: str
    is_stop_loss: bool


class DynamicExitEngine:
    def __init__(self, config: Optional[ExitConfig] = None):
        self.config = config or ExitConfig()

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
        liquidity_usd: float
    ) -> ExitVerdict:
        pnl_pct = ((current_price - entry_price) / max(entry_price, 1e-9)) * 100.0
        peak_gain_pct = ((peak_price - entry_price) / max(entry_price, 1e-9)) * 100.0
        duration_minutes = (current_time - entry_time) / 60.0

        # 1. Hard Stop Loss
        if pnl_pct <= -self.config.stop_loss_percent:
            return ExitVerdict(
                should_exit=True,
                sell_ratio=1.0,
                exit_reason=f"STOP_LOSS_TRIGGERED ({pnl_pct:.1f}% <= -{self.config.stop_loss_percent:.1f}%)",
                is_stop_loss=True
            )

        # 2. Trailing Stop
        if peak_gain_pct >= self.config.trailing_stop_activation_percent:
            drawdown_from_peak_pct = ((peak_price - current_price) / max(peak_price, 1e-9)) * 100.0
            if drawdown_from_peak_pct >= self.config.trailing_stop_distance_percent:
                return ExitVerdict(
                    should_exit=True,
                    sell_ratio=1.0,
                    exit_reason=f"TRAILING_STOP_TRIGGERED (Peak +{peak_gain_pct:.1f}%, Pullback -{drawdown_from_peak_pct:.1f}%)",
                    is_stop_loss=False
                )

        # 3. Take Profit Tier 3 (+150%)
        if pnl_pct >= self.config.take_profit_target_3_percent:
            return ExitVerdict(
                should_exit=True,
                sell_ratio=1.0,
                exit_reason=f"TAKE_PROFIT_TIER_3 (+{pnl_pct:.1f}% target hit)",
                is_stop_loss=False
            )

        # 4. Take Profit Tier 2 (+75%)
        if pnl_pct >= self.config.take_profit_target_2_percent:
            return ExitVerdict(
                should_exit=True,
                sell_ratio=self.config.take_profit_target_2_sell_ratio,
                exit_reason=f"TAKE_PROFIT_TIER_2 (+{pnl_pct:.1f}% target hit)",
                is_stop_loss=False
            )

        # 5. Take Profit Tier 1 (+30%)
        if pnl_pct >= self.config.take_profit_target_1_percent:
            return ExitVerdict(
                should_exit=True,
                sell_ratio=self.config.take_profit_target_1_sell_ratio,
                exit_reason=f"TAKE_PROFIT_TIER_1 (+{pnl_pct:.1f}% target hit)",
                is_stop_loss=False
            )

        # 6. Smart Money / Whale Dump Exit
        if self.config.exit_on_smart_money_dump and smart_money_score < 30.0 and whale_netflow < -25_000.0:
            return ExitVerdict(
                should_exit=True,
                sell_ratio=1.0,
                exit_reason="SMART_MONEY_DUMP_DETECTED (Whale net selling)",
                is_stop_loss=False
            )

        # 7. Regime Breakdown Exit (R8 Distribution / R9 Collapse)
        if regime in ("R8_DISTRIBUTION", "R9_COLLAPSE"):
            return ExitVerdict(
                should_exit=True,
                sell_ratio=1.0,
                exit_reason=f"REGIME_BREAKDOWN ({regime})",
                is_stop_loss=False
            )

        # 8. Time-based Max Holding Decay
        if duration_minutes > self.config.max_holding_time_minutes and pnl_pct < 5.0:
            return ExitVerdict(
                should_exit=True,
                sell_ratio=1.0,
                exit_reason=f"MAX_HOLDING_TIME_EXPIRED ({duration_minutes:.0f}m)",
                is_stop_loss=False
            )

        return ExitVerdict(should_exit=False, sell_ratio=0.0, exit_reason="HOLD", is_stop_loss=False)
