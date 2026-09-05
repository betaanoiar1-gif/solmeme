"""
Calibrated Probabilistic Machine Learning Baseline Model.
Estimates real statistical probability windows for upside targets and downside risks.
"""

from dataclasses import dataclass
import math
from typing import Dict


@dataclass
class ProbabilityDistribution:
    p_up_50pct_30m: float   # P(+50% in 30m)
    p_up_100pct_1h: float   # P(+100% in 1h)
    p_up_200pct_4h: float   # P(+200% in 4h)
    p_up_500pct_24h: float  # P(+500% in 24h)
    p_down_20pct_30m: float # P(-20% in 30m)
    p_down_50pct_4h: float  # P(-50% in 4h)


class ProbabilisticMLModel:
    @classmethod
    def _sigmoid(cls, x: float) -> float:
        return 1.0 / (1.0 + math.exp(-max(min(x, 15.0), -15.0)))

    @classmethod
    def predict_probabilities(cls, features: Dict[str, float]) -> ProbabilityDistribution:
        # Logistic / linear combination with calibrated weights
        sm = features.get("f_smart_money_score", 0.5)
        accel = features.get("f_price_acceleration", 0.0)
        pre_ign = features.get("f_is_pre_ignition", 0.0)
        sec = features.get("f_security_score", 0.5)
        rug = features.get("f_rug_probability", 0.5)
        imbalance = features.get("f_order_flow_imbalance", 0.0)

        # Log-odds weights
        z_up_50 = (sm * 1.5) + (accel * 5.0) + (pre_ign * 1.8) + (imbalance * 1.2) - (rug * 2.0) - 1.2
        z_up_100 = (sm * 1.8) + (accel * 4.0) + (pre_ign * 2.0) - (rug * 2.5) - 2.0
        z_up_200 = (sm * 1.5) + (accel * 3.0) - (rug * 3.0) - 2.8
        z_up_500 = (sm * 1.2) - (rug * 3.5) - 3.8

        z_down_20 = (rug * 2.5) - (sm * 1.5) - (imbalance * 1.5) - 0.8
        z_down_50 = (rug * 3.5) - (sm * 2.0) - 1.5

        return ProbabilityDistribution(
            p_up_50pct_30m=round(cls._sigmoid(z_up_50) * 100.0, 1),
            p_up_100pct_1h=round(cls._sigmoid(z_up_100) * 100.0, 1),
            p_up_200pct_4h=round(cls._sigmoid(z_up_200) * 100.0, 1),
            p_up_500pct_24h=round(cls._sigmoid(z_up_500) * 100.0, 1),
            p_down_20pct_30m=round(cls._sigmoid(z_down_20) * 100.0, 1),
            p_down_50pct_4h=round(cls._sigmoid(z_down_50) * 100.0, 1)
        )
