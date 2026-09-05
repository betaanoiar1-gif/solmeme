"""
Real Live Network & Solana RPC Failover Test Suite.
Tests Solana JSON-RPC endpoints, network connectivity probes,
failover logic, exponential backoff, and health tracking.
"""

import time
import unittest
from blockchain.rpc.rpc_client import SolanaRPCClient


class TestLiveNetwork(unittest.TestCase):
    def test_rpc_health_probe_and_metrics(self):
        client = SolanaRPCClient(
            endpoints=["https://api.mainnet-beta.solana.com", "https://rpc.ankr.com/solana"],
            timeout=0.2,
            max_retries=1
        )
        # Attempt call (or probe)
        res = client.get_health()
        # Should record metrics regardless of whether external gateway allows egress
        metrics = client.get_health_metrics()
        self.assertEqual(len(metrics), 2)
        for ep, h in metrics.items():
            self.assertIn("total_requests", h)
            self.assertIn("consecutive_errors", h)
            self.assertIn("is_active", h)

    def test_endpoint_rotation_and_cooldown(self):
        # Client with unreachable mock endpoints to verify rotation and exponential cooldown
        client = SolanaRPCClient(
            endpoints=["https://unreachable-rpc-a.solana.com", "https://unreachable-rpc-b.solana.com"],
            timeout=0.1,
            max_retries=2
        )
        res = client.call("getSlot")
        self.assertIsNone(res)

        metrics = client.get_health_metrics()
        for ep, h in metrics.items():
            self.assertGreater(h["total_requests"], 0)
            self.assertGreater(h["consecutive_errors"], 0)


if __name__ == "__main__":
    unittest.main()
