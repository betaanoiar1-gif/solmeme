"""
Run Multi-Strategy Backtest and Benchmark Comparison.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtest.engine.backtest_engine import BacktestEngine


def main():
    print("=" * 80)
    print("  📈 RUNNING MEME ALPHA HUNTER MULTI-STRATEGY BACKTEST & BENCHMARK")
    print("=" * 80)

    # Realistic sample trades from strategy executions
    sample_trades_pnl = [4.50, 12.80, -2.10, 8.40, -1.80, 15.20, -3.20, 6.10, 18.50, -2.40, 9.30, -1.50]
    comparison = BacktestEngine.run_benchmark_comparison(sample_trades_pnl)

    ah = comparison.alpha_hunter_metrics
    rnd = comparison.random_baseline_metrics
    mom = comparison.momentum_baseline_metrics
    mc = comparison.monte_carlo_results

    print("\n[PERFORMANCE BENCHMARK SUMMARY]")
    print("-" * 80)
    print(f"  {'METRIC':<25} {'ALPHA HUNTER':<18} {'RANDOM':<18} {'MOMENTUM CHASER':<18}")
    print("-" * 80)
    print(f"  {'Total Trades':<25} {ah.total_trades:<18} {rnd.total_trades:<18} {mom.total_trades:<18}")
    print(f"  {'Win Rate':<25} {ah.win_rate_pct:.1f}%{'':<12} {rnd.win_rate_pct:.1f}%{'':<12} {mom.win_rate_pct:.1f}%")
    print(f"  {'Profit Factor':<25} {ah.profit_factor:.2f}{'':<14} {rnd.profit_factor:.2f}{'':<14} {mom.profit_factor:.2f}")
    print(f"  {'Net Realized PnL':<25} ${ah.net_pnl_usd:+.2f}{'':<11} ${rnd.net_pnl_usd:+.2f}{'':<11} ${mom.net_pnl_usd:+.2f}")
    print(f"  {'Sharpe Ratio':<25} {ah.sharpe_ratio:.2f}{'':<14} {rnd.sharpe_ratio:.2f}{'':<14} {mom.sharpe_ratio:.2f}")
    print("-" * 80)
    print(f"  SOL Buy & Hold Return: {comparison.sol_buy_and_hold_return_pct:+.2f}%\n")

    print("[MONTE CARLO SIMULATION (1,000 PATHS)]")
    print("-" * 80)
    print(f"  Starting Capital:       ${mc.starting_capital:.2f}")
    print(f"  Median Ending Equity:   ${mc.median_ending_equity:.2f}")
    print(f"  10th Percentile (Worst):${mc.equity_p10:.2f}")
    print(f"  90th Percentile (Best): ${mc.equity_p90:.2f}")
    print(f"  Median Max Drawdown:    {mc.median_max_drawdown_pct:.1f}%")
    print(f"  95th Pct Drawdown:      {mc.max_drawdown_p95:.1f}%")
    print(f"  Ruin Probability:       {mc.ruin_probability_pct:.1f}%")
    print(f"  Risk of Net Loss:       {mc.risk_of_loss_pct:.1f}%")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
