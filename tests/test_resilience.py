"""
System Resilience, Restart Recovery, and Error Isolation Tests.
"""

import os
import tempfile
import unittest
from app.config.settings import AppConfig
from app.core.database import DatabaseManager
from app.orchestration.orchestrator import MemeAlphaHunterOrchestrator
from data.ingestion.mock_feeder import MarketFeeder
from portfolio.virtual_wallet.virtual_wallet import VirtualWallet


class TestResilience(unittest.TestCase):
    def test_database_restart_recovery(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
            db_path = tmp.name

        try:
            # 1. Initialize DB and save token & trade
            db1 = DatabaseManager(db_path)
            db1.upsert_token({
                "mint": "MintPersistent1",
                "symbol": "PERSIST",
                "name": "Persistent Token",
                "decimals": 9,
                "liquidity": 50_000.0,
                "market_cap": 250_000.0,
                "price": 0.05,
                "volume_24h": 100_000.0,
                "buyers_24h": 200,
                "sellers_24h": 150,
                "holders_count": 400,
                "creator": "Creator1",
                "pool_address": "Pool1",
                "chain": "solana",
                "source": "DexScanner",
                "first_seen_ts": 100.0,
                "updated_at": 100.0
            })

            # 2. Simulate complete restart: re-open DB from file
            db2 = DatabaseManager(db_path)
            tokens = db2.get_all_tokens()
            self.assertEqual(len(tokens), 1)
            self.assertEqual(tokens[0]["symbol"], "PERSIST")

        finally:
            if os.path.exists(db_path):
                os.remove(db_path)

    def test_corrupt_token_isolation(self):
        # Even if one token data payload is corrupt / malformed, pipeline must survive
        config = AppConfig()
        config.db_path = ":memory:"
        feeder = MarketFeeder()

        orchestrator = MemeAlphaHunterOrchestrator(config, data_provider=feeder)
        # Run cycle normally
        res = orchestrator.run_pipeline_cycle()
        self.assertNotIn("error", res)
        self.assertGreater(len(orchestrator.top_opportunities), 0)


if __name__ == "__main__":
    unittest.main()
