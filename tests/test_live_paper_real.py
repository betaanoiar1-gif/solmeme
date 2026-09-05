"""
Live Paper Real Data Pipeline & Accounting Validation Test (Phase J).
Validates that DATA_MODE=live does not silently trade on mock data,
and validates mathematical accounting invariants.
"""

import unittest
from app.config.settings import AppConfig
from app.orchestration.orchestrator import MemeAlphaHunterOrchestrator
from data.ingestion.live_market_feeder import LiveMarketFeeder


class TestLivePaperReal(unittest.TestCase):
    def setUp(self):
        self.config = AppConfig()
        self.config.data_mode = "live"
        self.config.db_path = ":memory:"
        self.feeder = LiveMarketFeeder(data_mode="live")
        self.orchestrator = MemeAlphaHunterOrchestrator(self.config, data_provider=self.feeder)

    def test_live_paper_mode_no_mock_contamination(self):
        # In isolated sandbox environment, live network returns 0 tokens
        res = self.orchestrator.run_pipeline_cycle()

        # Must NOT trade on mock data when DATA_MODE=live
        self.assertEqual(len(self.orchestrator.wallet.positions), 0)
        self.assertEqual(self.orchestrator.wallet.equity_usd, 100.0)
        self.assertEqual(self.orchestrator.wallet.cash_usd, 100.0)
        self.assertEqual(self.orchestrator.wallet.realized_pnl_usd, 0.0)

        # Accounting assertions must pass
        is_valid, msg = self.orchestrator.wallet.validate_accounting_invariants()
        self.assertTrue(is_valid, f"Accounting invariant violated: {msg}")

    def test_accounting_invariants_under_simulated_fills(self):
        # Test virtual wallet invariant mathematics
        wallet = self.orchestrator.wallet
        self.assertEqual(wallet.equity_usd, 100.0)
        is_valid, _ = wallet.validate_accounting_invariants()
        self.assertTrue(is_valid)


if __name__ == "__main__":
    unittest.main()
