"""
Relative Whale Strength Engine for Solana.
Calculates continuous multi-factor whale conviction without relying on a rigid nominal $20,000 threshold.
Combines:
1. Absolute verified flow
2. Flow relative to pool liquidity (flow / liquidity)
3. Single-order maximum pool impact
4. Repeated accumulation frequency
5. Buy volume acceleration
6. Distinct accumulating whale wallets
"""

from dataclasses import dataclass, field
import logging
import time
from typing import Any, Dict, List, Optional

from blockchain.parsers.real_swap_parser import RealSwapRecord
from blockchain.solana.types import Provenance, SourceType

logger = logging.getLogger("meme_alpha_hunter.relative_whale")


@dataclass
class RelativeWhaleMetrics:
    mint: str
    symbol: str
    pool_liquidity_usd: float
    absolute_netflow_usd: float
    flow_to_liquidity_ratio: float
    largest_single_buy_usd: float
    single_order_pool_impact_pct: float
    accumulating_whales_count: int
    accumulation_events_count: int
    whale_buy_acceleration: float
    relative_whale_strength_score: float  # 0 to 100
    conviction_tier: str  # "MEGA_WHALE_ACCUMULATION", "HIGH_RELATIVE_CONVICTION", "MODERATE_INFLOW", "NEUTRAL", "DISTRIBUTION"
    provenance: Provenance = field(default_factory=Provenance)


class RelativeWhaleEngine:
    WHALE_SWAP_MIN_USD = 2500.0 # Min order size to register as whale-tier swap

    @classmethod
    def evaluate_token(
        cls,
        mint: str,
        symbol: str,
        swaps: List[RealSwapRecord],
        pool_liquidity_usd: float = 1_000_000.0
    ) -> RelativeWhaleMetrics:
        """
        Calculates continuous Relative Whale Strength for a token.
        """
        whale_swaps = [s for s in swaps if (s.quote_amount_usd or 0.0) >= cls.WHALE_SWAP_MIN_USD]

        if not whale_swaps:
            return RelativeWhaleMetrics(
                mint=mint,
                symbol=symbol,
                pool_liquidity_usd=pool_liquidity_usd,
                absolute_netflow_usd=0.0,
                flow_to_liquidity_ratio=0.0,
                largest_single_buy_usd=0.0,
                single_order_pool_impact_pct=0.0,
                accumulating_whales_count=0,
                accumulation_events_count=0,
                whale_buy_acceleration=0.0,
                relative_whale_strength_score=50.0,
                conviction_tier="NEUTRAL",
                provenance=Provenance(source_type=SourceType.REAL, confidence=0.5)
            )

        whale_buys = [s for s in whale_swaps if s.side == "BUY"]
        whale_sells = [s for s in whale_swaps if s.side == "SELL"]

        buy_vol = sum(s.quote_amount_usd or 0.0 for s in whale_buys)
        sell_vol = sum(s.quote_amount_usd or 0.0 for s in whale_sells)
        netflow = buy_vol - sell_vol

        flow_to_liq = netflow / max(pool_liquidity_usd, 1.0)
        largest_buy = max([s.quote_amount_usd for s in whale_buys] or [0.0])
        single_order_impact_pct = (largest_buy / max(pool_liquidity_usd, 1.0)) * 100.0

        accum_wallets = set(s.wallet for s in whale_buys)
        accum_events = len(whale_buys)

        # Acceleration: volume in 2nd half vs 1st half
        if len(whale_buys) >= 2:
            mid = len(whale_buys) // 2
            v1 = sum(s.quote_amount_usd or 0.0 for s in whale_buys[:mid])
            v2 = sum(s.quote_amount_usd or 0.0 for s in whale_buys[mid:])
            accel = (v2 - v1) / max(v1, 1.0)
        else:
            accel = 0.0

        # Multi-factor score (0 to 100):
        # 1. Flow / Liquidity ratio (30%) -> 1.0% of pool is great (100 pts)
        rel_flow_score = min(max(flow_to_liq * 100.0 * 50.0, 0.0), 100.0) if netflow > 0 else 0.0
        # 2. Single-order pool impact (25%) -> 0.5% single buy is 100 pts
        impact_score = min(max(single_order_impact_pct * 200.0, 0.0), 100.0)
        # 3. Accumulation events / repeat buys (20%)
        events_score = min(accum_events * 25.0, 100.0)
        # 4. Number of distinct whale wallets (15%)
        wallets_score = min(len(accum_wallets) * 33.3, 100.0)
        # 5. Buy acceleration (10%)
        accel_score = min(max((accel + 0.5) * 50.0, 0.0), 100.0)

        composite_score = round(
            (rel_flow_score * 0.30) +
            (impact_score * 0.25) +
            (events_score * 0.20) +
            (wallets_score * 0.15) +
            (accel_score * 0.10),
            1
        )

        if netflow < -5000.0:
            composite_score = max(composite_score - 30.0, 10.0)
            tier = "DISTRIBUTION"
        elif composite_score >= 80.0:
            tier = "MEGA_WHALE_ACCUMULATION"
        elif composite_score >= 65.0:
            tier = "HIGH_RELATIVE_CONVICTION"
        elif composite_score >= 55.0:
            tier = "MODERATE_INFLOW"
        else:
            tier = "NEUTRAL"

        return RelativeWhaleMetrics(
            mint=mint,
            symbol=symbol,
            pool_liquidity_usd=pool_liquidity_usd,
            absolute_netflow_usd=round(netflow, 2),
            flow_to_liquidity_ratio=round(flow_to_liq, 6),
            largest_single_buy_usd=round(largest_buy, 2),
            single_order_pool_impact_pct=round(single_order_impact_pct, 4),
            accumulating_whales_count=len(accum_wallets),
            accumulation_events_count=accum_events,
            whale_buy_acceleration=round(accel, 2),
            relative_whale_strength_score=composite_score,
            conviction_tier=tier,
            provenance=Provenance(source_type=SourceType.REAL, confidence=1.0, verified_on_chain=True)
        )
