"""
Monte Carlo Simulation Engine with sample size validation.
"""

from dataclasses import dataclass
import random
from typing import Dict, List, Optional


@dataclass
class MonteCarloResult:
    iterations: int
    starting_capital: float
    status: str  # "VALID_SAMPLE", "INSUFFICIENT_SAMPLE"
    trades_sample_size: int
    median_ending_equity: float
    equity_p10: float
    equity_p90: float
    median_max_drawdown_pct: float
    max_drawdown_p95: float
    ruin_probability_pct: float
    risk_of_loss_pct: float


class MonteCarloEngine:
    MIN_TRADES_REQUIRED = 8

    @classmethod
    def simulate(
        cls,
        trades_pnl: List[float],
        starting_capital: float = 100.0,
        iterations: int = 1000,
        horizon_trades: int = 50
    ) -> MonteCarloResult:
        sample_size = len(trades_pnl)

        if sample_size < cls.MIN_TRADES_REQUIRED:
            return MonteCarloResult(
                iterations=iterations,
                starting_capital=starting_capital,
                status=f"INSUFFICIENT_SAMPLE ({sample_size}/{cls.MIN_TRADES_REQUIRED} trades min)",
                trades_sample_size=sample_size,
                median_ending_equity=starting_capital,
                equity_p10=starting_capital,
                equity_p90=starting_capital,
                median_max_drawdown_pct=0.0,
                max_drawdown_p95=0.0,
                ruin_probability_pct=0.0,
                risk_of_loss_pct=0.0
            )

        ending_equities = []
        max_drawdowns = []
        ruin_count = 0
        loss_count = 0

        for _ in range(iterations):
            equity = starting_capital
            peak = starting_capital
            max_dd = 0.0

            for _ in range(horizon_trades):
                pnl = random.choice(trades_pnl)
                equity += pnl
                if equity > peak:
                    peak = equity
                dd = ((peak - equity) / max(peak, 1e-9)) * 100.0
                if dd > max_dd:
                    max_dd = dd

                if equity <= (starting_capital * 0.5):
                    break

            ending_equities.append(equity)
            max_drawdowns.append(max_dd)

            if equity <= (starting_capital * 0.5):
                ruin_count += 1
            if equity < starting_capital:
                loss_count += 1

        ending_equities.sort()
        max_drawdowns.sort()

        p10_idx = int(0.10 * iterations)
        p50_idx = int(0.50 * iterations)
        p90_idx = int(0.90 * iterations)
        p95_idx = int(0.95 * iterations)

        return MonteCarloResult(
            iterations=iterations,
            starting_capital=starting_capital,
            status="VALID_SAMPLE",
            trades_sample_size=sample_size,
            median_ending_equity=round(ending_equities[p50_idx], 2),
            equity_p10=round(ending_equities[p10_idx], 2),
            equity_p90=round(ending_equities[p90_idx], 2),
            median_max_drawdown_pct=round(max_drawdowns[p50_idx], 2),
            max_drawdown_p95=round(max_drawdowns[p95_idx], 2),
            ruin_probability_pct=round((ruin_count / iterations) * 100.0, 2),
            risk_of_loss_pct=round((loss_count / iterations) * 100.0, 2)
        )
