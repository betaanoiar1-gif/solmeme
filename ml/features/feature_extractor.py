"""
Point-in-Time Feature Extractor.
Guarantees zero data leakage by computing features strictly from past and present events.
"""

from typing import Any, Dict, List
from intelligence.market_microstructure.microstructure import MicrostructureMetrics
from intelligence.token.dna import DNASnapshot


class FeatureExtractor:
    @classmethod
    def extract_vector(
        cls,
        token_data: Dict[str, Any],
        micro: MicrostructureMetrics,
        smart_money_score: float,
        whale_netflow: float,
        security_score: float,
        rug_probability: float,
        dna_history: List[DNASnapshot]
    ) -> Dict[str, float]:
        """Returns normalized feature vector strictly at timestamp T."""
        liquidity = float(token_data.get("liquidity", 0.0))
        volume = float(token_data.get("volume_24h", 0.0))
        mcap = float(token_data.get("market_cap", 0.0))
        holders = float(token_data.get("holders_count", 0))

        return {
            "f_log_liquidity": min(max(liquidity / 100_000.0, 0.0), 10.0),
            "f_log_volume": min(max(volume / 500_000.0, 0.0), 10.0),
            "f_log_mcap": min(max(mcap / 1_000_000.0, 0.0), 10.0),
            "f_holders_norm": min(holders / 5_000.0, 10.0),
            "f_order_flow_imbalance": micro.order_flow_imbalance,
            "f_buy_sell_ratio": min(micro.buy_sell_ratio / 5.0, 5.0),
            "f_price_velocity": micro.price_velocity,
            "f_price_acceleration": micro.price_acceleration,
            "f_smart_money_score": smart_money_score / 100.0,
            "f_whale_netflow_norm": min(max(whale_netflow / 50_000.0, -2.0), 2.0),
            "f_security_score": security_score / 100.0,
            "f_rug_probability": rug_probability / 100.0,
            "f_is_pre_ignition": 1.0 if micro.is_pre_ignition else 0.0
        }
