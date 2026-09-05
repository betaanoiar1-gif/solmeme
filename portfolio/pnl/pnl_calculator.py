"""
PnL and Returns Accounting Engine.
Calculates realized, unrealized, net returns, Sharpe, Sortino, and Profit Factor.
"""

from dataclasses import dataclass
import math
from typing import List


@dataclass
class PerformanceMetrics:
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate_pct: float
    realized_pnl_usd: float
    total_fees_usd: float
    total_slippage_usd: float
    net_pnl_usd: float
    profit_factor: float
    average_trade_pnl_usd: float
    average_win_usd: float
    average_loss_usd: float
    max_win_usd: float
    max_loss_usd: float
    expectancy_usd: float
    sharpe_ratio: float
    sortino_ratio: float


class PnLCalculator:
    @classmethod
    def compute_metrics(
        cls,
        trades_pnl: List[float],
        total_fees: float = 0.0,
        total_slippage: float = 0.0
    ) -> PerformanceMetrics:
        if not trades_pnl:
            return PerformanceMetrics(
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate_pct=0.0,
                realized_pnl_usd=0.0,
                total_fees_usd=total_fees,
                total_slippage_usd=total_slippage,
                net_pnl_usd=-total_fees - total_slippage,
                profit_factor=0.0,
                average_trade_pnl_usd=0.0,
                average_win_usd=0.0,
                average_loss_usd=0.0,
                max_win_usd=0.0,
                max_loss_usd=0.0,
                expectancy_usd=0.0,
                sharpe_ratio=0.0,
                sortino_ratio=0.0
            )

        wins = [p for p in trades_pnl if p > 0]
        losses = [p for p in trades_pnl if p <= 0]

        total_trades = len(trades_pnl)
        win_count = len(wins)
        loss_count = len(losses)
        win_rate = (win_count / total_trades) * 100.0

        gross_profit = sum(wins)
        gross_loss = abs(sum(losses))
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (99.0 if gross_profit > 0 else 0.0)

        realized_pnl = sum(trades_pnl)
        net_pnl = realized_pnl  # Already net of trade execution fees if calculated at trade level

        avg_win = (sum(wins) / win_count) if win_count > 0 else 0.0
        avg_loss = (sum(losses) / loss_count) if loss_count > 0 else 0.0
        avg_trade = realized_pnl / total_trades

        win_prob = win_count / total_trades
        loss_prob = loss_count / total_trades
        expectancy = (win_prob * avg_win) + (loss_prob * avg_loss)

        # Sharpe / Sortino approximation
        mean_r = avg_trade
        std_r = math.sqrt(sum((p - mean_r) ** 2 for p in trades_pnl) / max(total_trades - 1, 1)) if total_trades > 1 else 1.0
        downside_std = math.sqrt(sum((p) ** 2 for p in losses) / max(loss_count, 1)) if loss_count > 0 else 1.0

        sharpe = (mean_r / max(std_r, 1e-6)) * math.sqrt(total_trades)
        sortino = (mean_r / max(downside_std, 1e-6)) * math.sqrt(total_trades)

        return PerformanceMetrics(
            total_trades=total_trades,
            winning_trades=win_count,
            losing_trades=loss_count,
            win_rate_pct=round(win_rate, 2),
            realized_pnl_usd=round(realized_pnl, 2),
            total_fees_usd=round(total_fees, 2),
            total_slippage_usd=round(total_slippage, 2),
            net_pnl_usd=round(net_pnl, 2),
            profit_factor=round(profit_factor, 2),
            average_trade_pnl_usd=round(avg_trade, 2),
            average_win_usd=round(avg_win, 2),
            average_loss_usd=round(avg_loss, 2),
            max_win_usd=round(max(wins) if wins else 0.0, 2),
            max_loss_usd=round(min(losses) if losses else 0.0, 2),
            expectancy_usd=round(expectancy, 2),
            sharpe_ratio=round(sharpe, 2),
            sortino_ratio=round(sortino, 2)
        )
