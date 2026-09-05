"""
End-to-End Integration Test for Live Paper Pipeline.
Tests the complete DISCOVER -> FILTER -> UNDERSTAND -> SCORE -> RANK -> SIMULATE -> MONITOR -> LEARN loop.
"""

import unittest
from app.config.settings import AppConfig
from app.orchestration.orchestrator import MemeAlphaHunterOrchestrator
from data.ingestion.mock_feeder import MarketFeeder


class TestE2ELivePaper(unittest.TestCase):
    def setUp(self):
        self.config = AppConfig()
        self.config.data_mode = "mock"
        self.config.db_path = ":memory:"
        self.feeder = MarketFeeder()
        self.orchestrator = MemeAlphaHunterOrchestrator(self.config, data_provider=self.feeder)

    def test_full_pipeline_execution(self):
        # 1. Initial State
        self.assertEqual(self.orchestrator.wallet.cash_usd, 100.0)
        self.assertEqual(self.orchestrator.wallet.equity_usd, 100.0)

        # 2. Run Cycle 1: Discover, filter, score, and open paper entries
        res1 = self.orchestrator.run_pipeline_cycle()
        self.assertNotIn("error", res1)
        self.assertGreater(len(self.orchestrator.top_opportunities), 0)
        self.assertGreater(len(self.orchestrator.wallet.positions), 0)
        self.assertLess(self.orchestrator.wallet.cash_usd, 100.0)

        # Verify dangerous honeypot was rejected
        honeypot_rejections = [r for r in self.orchestrator.rejected_tokens if "HONEYSCAM" in r["symbol"]]
        self.assertEqual(len(honeypot_rejections), 1)

        # 3. Simulate market advance over multiple cycles to trigger dynamic exits
        for _ in range(12):
            self.feeder.tick_market(drift_factor=0.08)
            self.orchestrator.run_pipeline_cycle()

        summary = self.orchestrator.wallet.get_summary()
        self.assertGreater(summary["equity"], 0.0)
        self.assertGreaterEqual(summary["total_fees"], 0.0)
        self.assertGreaterEqual(summary["total_slippage"], 0.0)

        # Verify journal captured trades
        trades = self.orchestrator.journal.records
        self.assertGreater(len(trades), 0)
        for t in trades:
            self.assertIsNotNone(t.trade_id)
            self.assertIsNotNone(t.exit_reason)
            self.assertIsNotNone(t.realized_pnl)


if __name__ == "__main__":
    unittest.main()
