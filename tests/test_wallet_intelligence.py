"""
Tests for Wallet Intelligence, Whale Radar, Cluster Graph, and Creator Tracking.
"""

import unittest
from intelligence.creator.creator_tracker import CreatorTracker
from intelligence.smart_money.smart_engine import SmartMoneyEngine
from intelligence.wallet_graph.cluster_graph import WalletClusterGraph
from intelligence.whales.whale_radar import WhaleRadar


class TestWalletIntelligence(unittest.TestCase):
    def test_whale_radar_buy_and_accumulation(self):
        radar = WhaleRadar()
        trade1 = {
            "signer": "WhaleAlpha1",
            "token_mint": "MintABC",
            "type": "BUY",
            "usd_amount": 10_000.0,
            "token_amount": 100_000.0,
            "price_usd": 0.10
        }
        sig1 = radar.process_trade(trade1, token_liquidity=50_000.0)
        self.assertIsNotNone(sig1)
        self.assertEqual(sig1.action, "WHALE_BUY")

        # Process 3 more buys -> Accumulation
        for _ in range(3):
            sig_acc = radar.process_trade(trade1, token_liquidity=50_000.0)
        self.assertEqual(sig_acc.action, "WHALE_ACCUMULATION")

    def test_wallet_cluster_discount(self):
        graph = WalletClusterGraph()
        funder = "FunderMaster1"
        for i in range(5):
            graph.register_funding(funder, f"SubWallet_{i}")

        res = graph.analyze_token_wallets([f"SubWallet_{i}" for i in range(5)])
        self.assertEqual(res.total_wallets, 5)
        self.assertEqual(res.independent_clusters, 1)  # All 5 belong to 1 single cluster
        self.assertLess(res.cluster_discount_factor, 0.5)

    def test_creator_tracking(self):
        tracker = CreatorTracker()
        scam_prof = tracker.get_creator_reputation("ScammerDev1111111111111111111111111111111")
        self.assertTrue(scam_prof.is_blacklisted)
        self.assertEqual(scam_prof.reputation_score, 0.0)


if __name__ == "__main__":
    unittest.main()
