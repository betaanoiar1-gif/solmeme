"""
Tests for Token Discovery and Pool Scanner.
"""

import unittest
from app.config.settings import DiscoveryConfig
from app.core.database import DatabaseManager
from data.ingestion.mock_feeder import MarketFeeder
from discovery.token_discovery.token_scanner import TokenDiscoveryScanner
from discovery.pool_discovery.pool_scanner import PoolDiscoveryScanner
from blockchain.solana.types import LiquidityPool


class TestDiscovery(unittest.TestCase):
    def setUp(self):
        self.db = DatabaseManager(":memory:")
        self.feeder = MarketFeeder()
        self.scanner = TokenDiscoveryScanner(self.feeder, DiscoveryConfig(), self.db)

    def test_token_discovery_scan(self):
        tokens = self.scanner.scan(limit=10)
        self.assertGreater(len(tokens), 0)
        symbols = [t.symbol for t in tokens]
        self.assertIn("BONK", symbols)
        self.assertIn("WIF", symbols)

    def test_low_liquidity_filtering(self):
        tokens = self.scanner.scan(limit=20)
        thin = next((t for t in tokens if t.symbol == "THINLIQ"), None)
        self.assertIsNotNone(thin)
        self.assertFalse(thin.is_qualified)
        self.assertIn("Liquidity", thin.rejection_reason)

    def test_pool_scanner(self):
        pool_scanner = PoolDiscoveryScanner()
        pool = LiquidityPool(
            pool_address="Pool123",
            token_mint="Mint456",
            liquidity_usd=50_000.0,
            price_usd=0.05
        )
        pool_scanner.register_pool(pool)
        found = pool_scanner.get_pool_by_mint("Mint456")
        self.assertEqual(found.pool_address, "Pool123")


if __name__ == "__main__":
    unittest.main()
