"""
Regression Test Suite for Meme Alpha Hunter.
Verifies no regressions in edge case handling, fee calculations, and stage transitions.
"""

import unittest
from app.config.settings import AppConfig
from intelligence.market_microstructure.microstructure import MarketMicrostructureEngine
from scoring.opportunity.opportunity_scorer import OpportunityScorer
from security.rug_detection.rug_engine import SecurityEvaluation
from simulation.fees.fee_calculator import FeeCalculator
from sniper.execution.state_machine import SniperStage, SniperStateMachine


class TestRegression(unittest.TestCase):
    def test_fee_calculator_non_zero(self):
        config = AppConfig().execution
        fees = FeeCalculator.calculate(10.0, config)
        self.assertGreater(fees.total_fee_usd, 0.0)
        self.assertAlmostEqual(fees.total_fee_usd, fees.dex_lp_fee_usd + fees.solana_base_fee_usd + fees.priority_fee_usd, places=4)

    def test_sniper_stage_state_transitions(self):
        sm = SniperStateMachine()
        mint = "MintXYZ"
        self.assertEqual(sm.get_state(mint), SniperStage.S0_WATCH)
        sm.transition(mint, SniperStage.S3_SNIPER_READY)
        self.assertEqual(sm.get_state(mint), SniperStage.S3_SNIPER_READY)
        sm.transition(mint, SniperStage.S4_PAPER_EXECUTION)
        self.assertEqual(sm.get_state(mint), SniperStage.S4_PAPER_EXECUTION)
        sm.transition(mint, SniperStage.SX_KILL)
        self.assertEqual(sm.get_state(mint), SniperStage.SX_KILL)

    def test_hard_reject_overrides_high_alpha(self):
        # A token with high volume/buyers but failing security must be hard rejected
        sec_eval = SecurityEvaluation("BadToken", 0.0, 100.0, False, False, 0.0, 95.0, 80.0, True, False, "HARD_REJECT", ["HONEYPOT"], 100.0)
        token_data = {"mint": "BadToken", "symbol": "BAD", "liquidity": 10_000.0, "volume_24h": 500_000.0, "buyers_24h": 1000, "sellers_24h": 10}
        micro = MarketMicrostructureEngine.compute("BadToken", token_data, [], 90.0, 50_000.0)
        from intelligence.narrative.narrative_engine import NarrativeMetrics
        nar = NarrativeMetrics("Scam", 1, 1000.0, 50.0, 0.0, 0.0, "Exhausted")

        scorer = OpportunityScorer()
        opp = scorer.evaluate_opportunity(token_data, sec_eval, micro, 90.0, 50_000.0, nar, [])
        self.assertEqual(opp.recommendation, "REJECT")
        self.assertLessEqual(opp.final_score, 25.0)


if __name__ == "__main__":
    unittest.main()
