"""
Tests for Token Security, Authority Checker, and Rug Pull Detection.
"""

import unittest
from app.config.settings import SecurityConfig
from app.core.database import DatabaseManager
from security.rug_detection.rug_engine import RugDetectionEngine
from security.token_security.authority_checker import AuthorityChecker
from security.liquidity_risk.liquidity_checker import LiquidityRiskChecker
from security.wallet_risk.concentration_checker import ConcentrationChecker


class TestSecurityEngine(unittest.TestCase):
    def setUp(self):
        self.db = DatabaseManager(":memory:")
        self.engine = RugDetectionEngine(SecurityConfig(), self.db)

    def test_safe_token_evaluation(self):
        safe_data = {
            "mint_auth_revoked": True,
            "freeze_auth_revoked": True,
            "lp_locked_pct": 100.0,
            "top10_holder_pct": 20.0,
            "dev_holding_pct": 1.0,
            "is_honeypot": False
        }
        res = self.engine.evaluate("SafeMint123", safe_data)
        self.assertEqual(res.status, "SAFE")
        self.assertGreaterEqual(res.security_score, 80.0)
        self.assertLessEqual(res.rug_probability, 20.0)

    def test_honeypot_hard_reject(self):
        scam_data = {
            "mint_auth_revoked": False,
            "freeze_auth_revoked": False,
            "lp_locked_pct": 0.0,
            "top10_holder_pct": 90.0,
            "dev_holding_pct": 70.0,
            "is_honeypot": True
        }
        res = self.engine.evaluate("ScamMint999", scam_data)
        self.assertEqual(res.status, "HARD_REJECT")
        self.assertGreaterEqual(res.rug_probability, 80.0)
        self.assertTrue(any("HONEYPOT" in r for r in res.rejection_reasons))

    def test_concentration_check(self):
        conc_data = {
            "top10_holder_pct": 85.0,
            "dev_holding_pct": 35.0
        }
        res = ConcentrationChecker.check(conc_data, max_top10_pct=65.0, max_dev_pct=15.0)
        self.assertFalse(res.is_acceptable)
        self.assertGreater(res.risk_points, 30.0)


if __name__ == "__main__":
    unittest.main()
