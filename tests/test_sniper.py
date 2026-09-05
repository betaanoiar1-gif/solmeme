"""
Tests for Sniper Modes, Anti-Sniper Defense, Chase Detector, and Dynamic Exits.
"""

import unittest
from app.config.settings import ExitConfig
from scoring.opportunity.opportunity_scorer import OpportunityReport
from sniper.early_launch.early_launch_sniper import EarlyLaunchSniper
from sniper.execution.anti_sniper import AntiSniperDefense
from sniper.execution.chase_detector import ChaseDetector
from sniper.execution.exit_engine import DynamicExitEngine
from sniper.execution.state_machine import SniperStage, SniperStateMachine
from sniper.hybrid.hybrid_sniper import HybridSniper
from sniper.smart_money.smart_money_sniper import SmartMoneySniper


class TestSniper(unittest.TestCase):
    def setUp(self):
        self.opp = OpportunityReport(
            mint="MintTest",
            symbol="TEST",
            alpha_score=82.0,
            risk_score=22.0,
            confidence_score=75.0,
            earlyness_score=85.0,
            execution_score=80.0,
            final_score=81.0,
            regime="R3_EARLY_IGNITION",
            narrative="AI Agents",
            recommendation="PAPER_ENTRY",
            why_ranked_high=[],
            why_not_higher=[],
            what_supports_it=[],
            what_could_invalidate_it=[],
            updated_at=100.0
        )

    def test_sniper_modes_qualification(self):
        self.assertTrue(EarlyLaunchSniper.evaluate(self.opp, age_minutes=35.0))
        self.assertTrue(SmartMoneySniper.evaluate(self.opp, smart_money_score=85.0, netflow_usd=10_000.0))
        self.assertTrue(HybridSniper.evaluate(self.opp, smart_money_score=85.0, whale_netflow=20_000.0, is_pre_ignition=True))

    def test_chase_detector(self):
        # Safe entry
        v_safe = ChaseDetector.evaluate_entry(0.04, 0.02, "R3_EARLY_IGNITION", 80.0)
        self.assertTrue(v_safe.is_safe_entry)
        self.assertEqual(v_safe.action, "EXECUTE_NOW")

        # Parabolic chase top
        v_chase = ChaseDetector.evaluate_entry(0.55, 0.20, "R7_EUPHORIA", 80.0)
        self.assertFalse(v_chase.is_safe_entry)
        self.assertEqual(v_chase.action, "WAIT_FOR_RETEST")

    def test_dynamic_exits(self):
        exit_engine = DynamicExitEngine(ExitConfig(stop_loss_percent=15.0, take_profit_target_1_percent=30.0))

        # Test Stop Loss Trigger (-18%)
        res_sl = exit_engine.evaluate_position(1.0, 0.82, 1.0, 0, 100, 50, 0, "R3", 50_000)
        self.assertTrue(res_sl.should_exit)
        self.assertTrue(res_sl.is_stop_loss)

        # Test Take Profit Trigger (+35%)
        res_tp = exit_engine.evaluate_position(1.0, 1.35, 1.35, 0, 100, 80, 10_000, "R3", 50_000)
        self.assertTrue(res_tp.should_exit)
        self.assertFalse(res_tp.is_stop_loss)


if __name__ == "__main__":
    unittest.main()
