"""
Tests for Backtest Engine, Monte Carlo, and Benchmarks.
"""

import unittest
from backtest.engine.backtest_engine import BacktestEngine
from backtest.monte_carlo.monte_carlo import MonteCarloEngine


class TestBacktest(unittest.TestCase):
    def test_monte_carlo_resampling(self):
        sample_pnls = [5.0, 10.0, -2.0, 4.0, -3.0, 8.0, 12.0, -4.0]
        res = MonteCarloEngine.simulate(sample_pnls, starting_capital=100.0, iterations=500, horizon_trades=30)
        self.assertEqual(res.iterations, 500)
        self.assertGreater(res.median_ending_equity, 100.0)
        self.assertLessEqual(res.ruin_probability_pct, 10.0)

    def test_benchmark_comparison(self):
        sample_pnls = [4.0, 8.0, -1.5, 6.0, 10.0, -2.0]
        comparison = BacktestEngine.run_benchmark_comparison(sample_pnls)
        self.assertGreater(comparison.alpha_hunter_metrics.profit_factor, 1.0)
        self.assertEqual(comparison.alpha_hunter_metrics.total_trades, 6)


if __name__ == "__main__":
    unittest.main()
