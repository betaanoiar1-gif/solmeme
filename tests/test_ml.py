"""
Tests for Feature Extraction (No Leakage) and Probabilistic Machine Learning Model.
"""

import unittest
from intelligence.market_microstructure.microstructure import MicrostructureMetrics
from ml.features.feature_extractor import FeatureExtractor
from ml.models.baseline_model import ProbabilisticMLModel


class TestML(unittest.TestCase):
    def test_feature_extraction_bounds(self):
        token_data = {"liquidity": 50_000.0, "volume_24h": 100_000.0, "market_cap": 500_000.0, "holders_count": 250}
        micro = MicrostructureMetrics("Mint1", 100, 20, 5.0, 0.67, 0.05, 0.02, 0.01, 0.20, 0.05, 3.5, True, "SMART_ACCUMULATION", False)
        features = FeatureExtractor.extract_vector(token_data, micro, 85.0, 25_000.0, 90.0, 10.0, [])

        self.assertIn("f_order_flow_imbalance", features)
        self.assertIn("f_smart_money_score", features)
        self.assertGreaterEqual(features["f_smart_money_score"], 0.0)
        self.assertLessEqual(features["f_smart_money_score"], 1.0)

    def test_probabilistic_model_inference(self):
        features = {
            "f_smart_money_score": 0.90,
            "f_price_acceleration": 0.05,
            "f_is_pre_ignition": 1.0,
            "f_security_score": 0.95,
            "f_rug_probability": 0.05,
            "f_order_flow_imbalance": 0.70
        }
        probs = ProbabilisticMLModel.predict_probabilities(features)
        self.assertGreater(probs.p_up_50pct_30m, probs.p_down_20pct_30m)
        self.assertGreaterEqual(probs.p_up_50pct_30m, 0.0)
        self.assertLessEqual(probs.p_up_50pct_30m, 100.0)


if __name__ == "__main__":
    unittest.main()
