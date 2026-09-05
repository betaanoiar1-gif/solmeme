"""
Real Solana Network & Address Validation Tests (Phase B & J).
Tests real Solana Base58 format verification, RPC failover, and synthetic address rejection.
"""

import unittest
from blockchain.rpc.rpc_client import SolanaRPCClient
from blockchain.solana.address_validator import SolanaAddressValidator
from data.ingestion.dex_provider import DexPublicProvider
from data.ingestion.live_market_feeder import LiveMarketFeeder


class TestLiveRealData(unittest.TestCase):
    def test_solana_address_validator_valid_mints(self):
        # Real Solana Mint Addresses
        real_mints = [
            "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",  # BONK
            "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm",  # WIF
            "7GCihgDB8fe6KNjn2MYtkzZcRjQy3t9GHdC8uHYmW2hr",  # POPCAT
            "So11111111111111111111111111111111111111112",  # WSOL
            "6p6xgHyF7AeQHyVaKVUz8V8bEkP1wX2MSo1111111111"   # TRUMP
        ]
        for mint in real_mints:
            self.assertTrue(SolanaAddressValidator.validate_token_mint(mint), f"Failed for {mint}")

    def test_solana_address_validator_reject_synthetic(self):
        # Invalid / Synthetic addresses (invalid characters like 0, O, I, l or invalid lengths)
        invalid_mints = [
            "00000000000000000000000000000000",          # '0' is not in Base58
            "IIIIIIIIIIIIIIIIIIIIIIIIIIIIIIII",          # 'I' is not in Base58
            "llIlllllIlllllIlllllIlllllIllll",           # 'l' is not in Base58
            "short",                                     # Too short (< 32 chars)
            "12345",
            "11111111111111111111111111111111",          # System program (rejected as token mint)
        ]
        for mint in invalid_mints:
            self.assertFalse(SolanaAddressValidator.validate_token_mint(mint), f"Should reject {mint}")

    def test_rpc_failover_and_health_tracking(self):
        # Provide multiple unreachable/bad endpoints to test graceful failover and cooldown
        client = SolanaRPCClient(
            endpoints=["https://unreachable-rpc-1.solana.com", "https://unreachable-rpc-2.solana.com"],
            timeout=0.1,
            max_retries=2
        )
        res = client.call("getHealth")
        self.assertIsNone(res)

        health_metrics = client.get_health_metrics()
        self.assertGreater(len(health_metrics), 0)
        for ep, h in health_metrics.items():
            self.assertGreater(h["total_requests"], 0)
            self.assertGreater(h["consecutive_errors"], 0)

    def test_live_feeder_strict_provenance_mode(self):
        feeder = LiveMarketFeeder(data_mode="live")
        self.assertEqual(feeder.source_type.value, "REAL")
        self.assertEqual(feeder.provider_name, "SolanaLiveMainnet")


if __name__ == "__main__":
    unittest.main()
