"""
Tests for Multi-Factor Scoring, Microstructure, and Regime Classification.
"""

import unittest
from app.config.settings import ScoringConfig
from intelligence.market_microstructure.microstructure import MarketMicrostructureEngine
from intelligence.narrative.narrative_engine import NarrativeMetrics
from intelligence.token.dna import DNASnapshot
from scoring.alpha_score.alpha_calculator import AlphaCalculator
from scoring.opportunity.opportunity_scorer import OpportunityScorer
from scoring.regime.regime_engine import MarketRegime, RegimeEngine
from scoring.risk_score.risk_calculator import RiskCalculator
from security.rug_detection.rug_engine import SecurityEvaluation


class TestScoring(unittest.TestCase):
    def setUp(self):
        self.config = ScoringConfig()
        self.dna_history = [
            DNASnapshot(100.0, 0.10, 10_000.0, 50_000.0, 100, 0.0, 0.0),
            DNASnapshot(110.0, 0.11, 15_000.0, 55_000.0, 120, 1000.0, 2000.0),
            DNASnapshot(120.0, 0.125, 25_000.0, 62_000.0, 150, 3000.0, 5000.0),
        ]

    def test_microstructure_and_pre_ignition(self):
        token_data = {"buyers_24h": 350, "sellers_24h": 50, "volume_24h": 200_000.0, "liquidity": 80_000.0}
        micro = MarketMicrostructureEngine.compute(
            mint="Mint123",
            token_data=token_data,
            dna_history=self.dna_history,
            smart_money_score=85.0,
            whale_netflow=30_000.0
        )
        self.assertGreater(micro.buy_sell_ratio, 2.0)
        self.assertGreater(micro.order_flow_imbalance, 0.5)
        self.assertTrue(micro.is_pre_ignition)

    def test_regime_classification(self):
        token_data = {"buyers_24h": 300, "sellers_24h": 80, "volume_24h": 150_000.0, "liquidity": 75_000.0}
        micro = MarketMicrostructureEngine.compute(
            mint="Mint123",
            token_data=token_data,
            dna_history=self.dna_history,
            smart_money_score=80.0,
            whale_netflow=20_000.0
        )
        regime = RegimeEngine.classify(token_data, micro, smart_money_score=80.0, whale_netflow=20_000.0)
        self.assertIn(regime, (MarketRegime.R3_EARLY_IGNITION, MarketRegime.R4_CONFIRMED_IGNITION, MarketRegime.R5_EXPANSION, MarketRegime.R2_ACCUMULATION))

    def test_alpha_and_opportunity_scoring(self):
        token_data = {
            "mint": "MintAlpha",
            "symbol": "ALPHA",
            "liquidity": 80_000.0,
            "volume_24h": 150_000.0,
            "holders_count": 500,
            "buyers_24h": 450,
            "sellers_24h": 75
        }
        sec_eval = SecurityEvaluation("MintAlpha", 90.0, 10.0, True, True, 100.0, 25.0, 2.0, False, False, "SAFE", [], 100.0)
        micro = MarketMicrostructureEngine.compute("MintAlpha", token_data, self.dna_history, 85.0, 20_000.0)
        nar = NarrativeMetrics("AI Agents", 3, 500_000.0, 80.0, 0.25, 0.3, "Emerging Narrative")

        scorer = OpportunityScorer(self.config)
        opp = scorer.evaluate_opportunity(token_data, sec_eval, micro, 85.0, 20_000.0, nar, self.dna_history)

        self.assertGreaterEqual(opp.alpha_score, 65.0)
        self.assertLessEqual(opp.risk_score, 30.0)
        self.assertEqual(opp.recommendation, "PAPER_ENTRY")


if __name__ == "__main__":
    unittest.main()
