"""
Tests for Execution Simulator, Slippage, Fees, Latency, and Partial Fills.
"""

import unittest
from app.config.settings import ExecutionConfig
from simulation.execution.execution_engine import ExecutionSimulator
from simulation.fees.fee_calculator import FeeCalculator
from simulation.latency.latency_simulator import LatencySimulator
from simulation.partial_fills.partial_fill_model import PartialFillModel
from simulation.slippage.slippage_model import SlippageModel


class TestSimulation(unittest.TestCase):
    def setUp(self):
        self.config = ExecutionConfig()
        self.sim = ExecutionSimulator(self.config)

    def test_fee_calculation(self):
        fees = FeeCalculator.calculate(trade_size_usd=100.0, config=self.config)
        self.assertGreater(fees.dex_lp_fee_usd, 0.0)
        self.assertGreater(fees.total_fee_usd, 0.0)

    def test_slippage_and_price_impact(self):
        # Small order on deep pool -> low slippage
        slip_small = SlippageModel.calculate(1.0, 10.0, 1_000_000.0, True, self.config)
        self.assertLess(slip_small.total_slippage_pct, 1.0)

        # Large order on thin pool -> high slippage
        slip_large = SlippageModel.calculate(1.0, 100.0, 2_000.0, True, self.config)
        self.assertGreater(slip_large.total_slippage_pct, slip_small.total_slippage_pct)

    def test_partial_fills(self):
        # Request $1000 on $5000 pool -> capacity 5% is $250
        fill = PartialFillModel.calculate(1000.0, 5000.0, enable_partial=True)
        self.assertEqual(fill.filled_size_usd, 250.0)
        self.assertEqual(fill.unfilled_size_usd, 750.0)
        self.assertEqual(fill.fill_ratio, 0.25)

    def test_latency_simulation(self):
        profile = LatencySimulator.simulate(mode="fast")
        self.assertGreater(profile.latency_ms, 0)
        self.assertGreater(profile.execution_ts, profile.detection_ts)


if __name__ == "__main__":
    unittest.main()
