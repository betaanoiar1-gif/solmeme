"""
Solana Memecoin Market Regime Engine.
Classifies token lifecycle into 10 distinct phases (R0 to R9),
specifically alerting on R2->R3 Pre-ignition and R7 Euphoria/Distribution.
"""

from enum import Enum
from typing import Dict, Any
from intelligence.market_microstructure.microstructure import MicrostructureMetrics


class MarketRegime(str, Enum):
    R0_DEAD = "R0_DEAD"
    R1_DORMANT = "R1_DORMANT"
    R2_ACCUMULATION = "R2_ACCUMULATION"
    R3_EARLY_IGNITION = "R3_EARLY_IGNITION"
    R4_CONFIRMED_IGNITION = "R4_CONFIRMED_IGNITION"
    R5_EXPANSION = "R5_EXPANSION"
    R6_PARABOLIC = "R6_PARABOLIC"
    R7_EUPHORIA = "R7_EUPHORIA"
    R8_DISTRIBUTION = "R8_DISTRIBUTION"
    R9_COLLAPSE = "R9_COLLAPSE"


class RegimeEngine:
    @classmethod
    def classify(
        cls,
        token_data: Dict[str, Any],
        micro_metrics: MicrostructureMetrics,
        smart_money_score: float,
        whale_netflow: float
    ) -> MarketRegime:
        raw_vol = token_data.get("volume_24h")
        vol = float(raw_vol) if raw_vol is not None else 0.0
        raw_liq = token_data.get("liquidity")
        liq = float(raw_liq) if raw_liq is not None else 0.0
        v_price = micro_metrics.price_velocity
        buyers = micro_metrics.buy_count
        sellers = micro_metrics.sell_count

        if liq < 500.0 or (vol < 100.0 and buyers < 2):
            return MarketRegime.R0_DEAD

        if micro_metrics.is_fake_breakout or (v_price < -0.25 and sellers > buyers * 2):
            return MarketRegime.R9_COLLAPSE

        if whale_netflow < -50_000.0 and smart_money_score < 40.0:
            return MarketRegime.R8_DISTRIBUTION

        if v_price > 0.50 and smart_money_score < 50.0:
            return MarketRegime.R7_EUPHORIA

        if v_price > 0.30:
            return MarketRegime.R6_PARABOLIC

        if v_price > 0.10 and micro_metrics.buy_sell_ratio > 1.4:
            return MarketRegime.R5_EXPANSION

        if micro_metrics.is_pre_ignition or (micro_metrics.buy_sell_ratio > 1.5 and v_price > 0.02):
            return MarketRegime.R3_EARLY_IGNITION

        if micro_metrics.buy_sell_ratio > 1.3 and v_price > 0.05:
            return MarketRegime.R4_CONFIRMED_IGNITION

        if smart_money_score > 70.0 and abs(v_price) <= 0.05:
            return MarketRegime.R2_ACCUMULATION

        return MarketRegime.R1_DORMANT
