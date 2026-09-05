"""
Multi-Factor Alpha Score Calculator (0 to 100).
Blends Microstructure, Smart Money, Whale Radar, Momentum Acceleration, and Narrative.
"""

from app.config.settings import ScoringConfig
from intelligence.market_microstructure.microstructure import MicrostructureMetrics
from intelligence.narrative.narrative_engine import NarrativeMetrics


class AlphaCalculator:
    @classmethod
    def calculate(
        cls,
        micro: MicrostructureMetrics,
        smart_money_score: float,
        whale_netflow: float,
        narrative_metrics: NarrativeMetrics,
        config: ScoringConfig
    ) -> float:
        # 1. Microstructure subscore (0-100)
        imbalance_norm = (micro.order_flow_imbalance + 1.0) * 50.0  # map -1..1 to 0..100
        ratio_norm = min(micro.buy_sell_ratio * 30.0, 100.0)
        micro_score = imbalance_norm * 0.5 + ratio_norm * 0.5

        # 2. Smart Money subscore (0-100)
        sm_score = smart_money_score

        # 3. Whale subscore (0-100)
        whale_score = min(max(50.0 + (whale_netflow / 50_000.0) * 25.0, 0.0), 100.0)

        # 4. Momentum & Acceleration subscore (0-100)
        accel_score = min(max(50.0 + micro.price_acceleration * 200.0 + (30.0 if micro.is_pre_ignition else 0.0), 0.0), 100.0)

        # 5. Narrative Heat subscore (0-100) — If UNKNOWN, exclude dimension and reweight
        if narrative_metrics.heat_score is not None:
            nar_score = narrative_metrics.heat_score
            alpha = (
                micro_score * config.weight_microstructure +
                sm_score * config.weight_smart_money +
                whale_score * config.weight_whale_radar +
                accel_score * config.weight_momentum_acceleration +
                nar_score * config.weight_narrative_heat
            )
        else:
            remaining_weight = (
                config.weight_microstructure +
                config.weight_smart_money +
                config.weight_whale_radar +
                config.weight_momentum_acceleration
            )
            if remaining_weight > 0:
                alpha = (
                    (micro_score * config.weight_microstructure +
                     sm_score * config.weight_smart_money +
                     whale_score * config.weight_whale_radar +
                     accel_score * config.weight_momentum_acceleration) / remaining_weight
                )
            else:
                alpha = 50.0

        return round(min(max(alpha, 0.0), 100.0), 2)
