"""
Market Microstructure, Acceleration, and Divergence Engine.
Computes order-flow metrics, 1st/2nd order accelerations, pre-ignition signatures,
and Money vs Price divergences.
"""

from dataclasses import dataclass
from typing import Any, List

from intelligence.token.dna import DNASnapshot


@dataclass
class MicrostructureMetrics:
    mint: str
    buy_count: int
    sell_count: int
    buy_sell_ratio: float
    order_flow_imbalance: float  # -1.0 (all sells) to +1.0 (all buys)
    price_velocity: float
    price_acceleration: float
    price_second_order: float
    volume_acceleration: float
    liquidity_growth_rate: float
    buyer_acceleration: float
    is_pre_ignition: bool
    money_price_divergence: str  # "SMART_ACCUMULATION", "RETAIL_CHASE", "CONVERGENT_BULL", "CONVERGENT_BEAR"
    is_fake_breakout: bool


class MarketMicrostructureEngine:
    @classmethod
    def compute(
        cls,
        mint: str,
        token_data: dict[str, Any],
        dna_history: List[DNASnapshot],
        smart_money_score: float,
        whale_netflow: float
    ) -> MicrostructureMetrics:
        buyers = int(token_data.get("buyers_24h", 0))
        sellers = int(token_data.get("sellers_24h", 0))
        tot_tx = buyers + sellers

        buy_sell_ratio = buyers / max(sellers, 1)
        imbalance = (buyers - sellers) / max(tot_tx, 1)

        # Time-series features are evidence-gated. When a required historical
        # observation is missing, preserve that absence as neutral/zero rather
        # than inventing market movement.
        v_curr = 0.0
        accel = 0.0
        second_order = 0.0
        vol_accel = 0.0
        liq_growth = 0.0

        if len(dna_history) >= 2:
            p_curr = dna_history[-1].price
            p_prev1 = dna_history[-2].price
            if p_curr is not None and p_prev1 is not None and p_prev1 > 0:
                v_curr = (p_curr - p_prev1) / max(p_prev1, 1e-9)

            vol_curr = dna_history[-1].volume
            vol_prev = dna_history[-2].volume
            if vol_curr is not None and vol_prev is not None and vol_prev > 0:
                vol_accel = (vol_curr - vol_prev) / max(vol_prev, 1.0)

            liq_curr = dna_history[-1].liquidity
            liq_prev = dna_history[-2].liquidity
            if liq_curr is not None and liq_prev is not None and liq_prev > 0:
                liq_growth = (liq_curr - liq_prev) / max(liq_prev, 1.0)

        if len(dna_history) >= 3:
            p_curr = dna_history[-1].price
            p_prev1 = dna_history[-2].price
            p_prev2 = dna_history[-3].price
            if p_curr is not None and p_prev1 is not None and p_prev1 > 0:
                v_curr = (p_curr - p_prev1) / max(p_prev1, 1e-9)
            if p_prev1 is not None and p_prev2 is not None and p_prev2 > 0:
                v_prev = (p_prev1 - p_prev2) / max(p_prev2, 1e-9)
                accel = v_curr - v_prev

        if len(dna_history) >= 4:
            p_prev2 = dna_history[-3].price
            p_prev3 = dna_history[-4].price
            if p_prev2 is not None and p_prev3 is not None and p_prev3 > 0:
                v_prev2 = (p_prev2 - p_prev3) / max(p_prev3, 1e-9)
                if len(dna_history) >= 3:
                    p_prev1 = dna_history[-2].price
                    p_curr = dna_history[-1].price
                    if p_curr is not None and p_prev1 is not None and p_prev1 > 0 and p_prev2 is not None and p_prev2 > 0:
                        v_curr = (p_curr - p_prev1) / max(p_prev1, 1e-9)
                        v_prev = (p_prev1 - p_prev2) / max(p_prev2, 1e-9)
                        accel = v_curr - v_prev
                        accel_prev = v_prev - v_prev2
                        second_order = accel - accel_prev

        buyer_accel = buy_sell_ratio * (1.0 + imbalance)

        # A pre-ignition label requires actual time-series history.
        is_pre_ignition = (
            len(dna_history) >= 3 and
            buyer_accel > 1.8 and
            smart_money_score > 75.0 and
            liq_growth >= 0.0 and
            v_curr < 0.20
        )

        if smart_money_score > 80.0 and v_curr < 0.05:
            money_price_div = "SMART_ACCUMULATION"
        elif smart_money_score < 40.0 and v_curr > 0.15:
            money_price_div = "RETAIL_CHASE"
        elif v_curr > 0.05 and smart_money_score > 60.0:
            money_price_div = "CONVERGENT_BULL"
        else:
            money_price_div = "CONVERGENT_BEAR"

        is_fake_breakout = (
            len(dna_history) >= 2 and
            v_curr > 0.10 and
            vol_accel > 0.30 and
            smart_money_score < 35.0 and
            whale_netflow < 0.0
        )

        return MicrostructureMetrics(
            mint=mint,
            buy_count=buyers,
            sell_count=sellers,
            buy_sell_ratio=round(buy_sell_ratio, 2),
            order_flow_imbalance=round(imbalance, 3),
            price_velocity=round(v_curr, 4),
            price_acceleration=round(accel, 4),
            price_second_order=round(second_order, 4),
            volume_acceleration=round(vol_accel, 3),
            liquidity_growth_rate=round(liq_growth, 3),
            buyer_acceleration=round(buyer_accel, 2),
            is_pre_ignition=is_pre_ignition,
            money_price_divergence=money_price_div,
            is_fake_breakout=is_fake_breakout
        )
