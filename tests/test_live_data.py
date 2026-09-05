"""
Real Live Solana Data Intelligence Test Suite.
Tests on-chain mint verification, parsed swap decoding, whale tracking,
smart money reputation scoring, wallet cluster analysis, and on-chain security checks.
"""

import unittest
from blockchain.parsers.real_swap_parser import RealSwapParser, RealSwapRecord
from blockchain.solana.mint_verifier import OnChainMintVerifier
from data.real_mainnet_snapshots.real_mainnet_data import REAL_SOLANA_MAINNET_MINTS, REAL_SOLANA_MAINNET_PARSED_SWAPS
from intelligence.smart_money.real_smart_money import RealSmartMoneyEngine
from intelligence.wallet_graph.real_cluster_graph import RealClusterGraph
from intelligence.whales.real_whale_tracker import RealWhaleTracker
from security.rug_detection.real_security_engine import RealSecurityEngine


class TestLiveData(unittest.TestCase):
    def setUp(self):
        self.verifier = OnChainMintVerifier()
        self.parser = RealSwapParser()
        self.whale_tracker = RealWhaleTracker()
        self.smart_money = RealSmartMoneyEngine()
        self.cluster_graph = RealClusterGraph()
        self.security_engine = RealSecurityEngine(mint_verifier=self.verifier)

    def test_onchain_mint_verification_offline_behavior(self):
        # In offline sandbox, direct RPC call reports RPC_UNAVAILABLE
        bonk_mint = "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263"
        ver = self.verifier.verify_mint(bonk_mint)
        self.assertIn(ver.verification_status, ("RPC_UNAVAILABLE", "VERIFIED_ON_CHAIN"))

    def test_onchain_mint_verification_from_account_data(self):
        # Verify 9-step account parser from on-chain account data
        bonk_mint = "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263"
        bonk_data = REAL_SOLANA_MAINNET_MINTS[bonk_mint]
        ver = self.verifier.verify_from_account_data(bonk_mint, bonk_data)
        self.assertTrue(ver.is_valid_mint)
        self.assertEqual(ver.decimals, 5)
        self.assertTrue(ver.mint_auth_revoked)
        self.assertTrue(ver.freeze_auth_revoked)
        self.assertEqual(ver.owner_program, "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
        self.assertEqual(ver.verification_status, "VERIFIED_ON_CHAIN")

    def test_reject_invalid_mint_strings(self):
        # Invalid Base58 and non-mints
        invalid = "InvalidBase58String0000000000000000000"
        ver = self.verifier.verify_mint(invalid)
        self.assertFalse(ver.is_valid_mint)
        self.assertEqual(ver.verification_status, "INVALID_BASE58")

    def test_real_swap_parser_balance_deltas(self):
        tx = REAL_SOLANA_MAINNET_PARSED_SWAPS[0]
        swaps = self.parser.parse_transaction(tx, sol_price_usd=100.0)
        self.assertEqual(len(swaps), 1)
        s = swaps[0]
        self.assertEqual(s.side, "BUY")
        self.assertEqual(s.mint, "9BB6NFEcjBCtnNLFko2FqVQBq8HHM13kCyYcdQbgpump")
        self.assertAlmostEqual(s.token_amount, 48695.0, places=1)
        self.assertGreater(s.quote_amount_usd, 5000.0)
        self.assertTrue(s.is_whale)
        self.assertTrue(s.is_quote_verified)

    def test_real_whale_tracker_events(self):
        tx = REAL_SOLANA_MAINNET_PARSED_SWAPS[0]
        swaps = self.parser.parse_transaction(tx, sol_price_usd=100.0)
        swap = swaps[0]
        event = self.whale_tracker.process_real_swap(swap, pool_liquidity_usd=100_000.0)
        self.assertIsNotNone(event)
        self.assertIn(event.action, ("BUY", "ACCUMULATION"))
        self.assertGreater(self.whale_tracker.get_token_whale_netflow(swap.mint), 0.0)

    def test_real_smart_money_engine(self):
        tx = REAL_SOLANA_MAINNET_PARSED_SWAPS[1]
        swaps = self.parser.parse_transaction(tx, sol_price_usd=100.0)
        swap = swaps[0]
        profile = self.smart_money.process_real_swap(swap)
        self.assertIsNotNone(profile)
        self.assertGreater(profile.total_volume_usd, 0.0)

        sig = self.smart_money.evaluate_token_smart_money(swap.mint)
        self.assertIsNotNone(sig.smart_money_score)
        self.assertEqual(sig.mint, swap.mint)

    def test_wallet_cluster_graph_detection(self):
        # Simulate funding transfer
        self.cluster_graph.register_transfer("FunderWallet1111", "BuyerA", 5.0, "sig1", 100, 1700000000.0)
        self.cluster_graph.register_transfer("FunderWallet1111", "BuyerB", 5.0, "sig2", 100, 1700000000.0)

        res = self.cluster_graph.analyze_token_wallets("Mint123", ["BuyerA", "BuyerB"], {"BuyerA": 1000.0, "BuyerB": 1000.0})
        self.assertIn(res.classification, ("RELATED_WALLETS", "SYBIL_CLUSTER"))
        self.assertGreaterEqual(res.risk_multiplier, 1.5)

    def test_real_security_engine_with_verification(self):
        bonk_mint = "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263"
        bonk_data = REAL_SOLANA_MAINNET_MINTS[bonk_mint]
        ver = self.verifier.verify_from_account_data(bonk_mint, bonk_data)
        sec = self.security_engine.evaluate_token(bonk_mint, verification=ver, lp_locked_pct=100.0, dev_holding_pct=1.0)
        self.assertEqual(sec.mint_auth_status, "REVOKED_SAFE")
        self.assertEqual(sec.freeze_auth_status, "REVOKED_SAFE")
        self.assertEqual(sec.status, "SAFE")
        self.assertGreaterEqual(sec.security_score, 80.0)


if __name__ == "__main__":
    unittest.main()
