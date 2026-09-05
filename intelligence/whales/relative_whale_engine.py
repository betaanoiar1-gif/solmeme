"""
Relative Whale Strength Engine for Solana.
Calculates continuous multi-factor whale conviction without relying on a rigid nominal $20,000 threshold.
Zero fallback to default $1,000,000 pool liquidity.
Zero conversion of unknown USD quotes to 0.0.
Strict UNKNOWN (None) vs REAL ZERO (0.0) semantic integrity.
Strictly verified quotes only participate in whale analytics.
"""

from dataclasses import dataclass, field
import logging
import time
from typing import Any, Dict, List, Optional

from blockchain.parsers.real_swap_parser import RealSwapRecord
from blockchain.solana.types import Provenance, SourceType

logger = logging.getLogger("meme_alpha_hunter.relative_whale")


def is_swap_quote_verified(swap: RealSwapRecord) -> bool:
    """
    Strictly verifies whether a swap has a verified quote on-chain and RPC.
    """
    if swap.quote_amount_usd is None:
        return False
    if not getattr(swap, "is_quote_verified", False):
        return False
    prov = getattr(swap, "provenance", None)
    if prov is None:
        return False
    if not getattr(prov, "verified_on_chain", False):
        return False
    if hasattr(prov, "rpc_verified") and getattr(prov, "rpc_verified") is False:
        return False
    return True


@dataclass
class RelativeWhaleMetrics:
    mint: str
    symbol: str
    pool_liquidity_usd: Optional[float]
    absolute_netflow_usd: Optional[float]
    flow_to_liquidity_ratio: Optional[float]
    largest_single_buy_usd: Optional[float]
    single_order_pool_impact_pct: Optional[float]
    accumulating_whales_count: int
    accumulation_events_count: int
    whale_buy_acceleration: Optional[float]
    relative_whale_strength_score: float  # 0 to 100
    conviction_tier: str  # "MEGA_WHALE_ACCUMULATION", "HIGH_RELATIVE_CONVICTION", "MODERATE_INFLOW", "NEUTRAL", "DISTRIBUTION"
    quote_quality: float = 1.0
    provenance: Provenance = field(default_factory=Provenance)


class RelativeWhaleEngine:
    WHALE_SWAP_MIN_USD = 2500.0 # Min order size to register as whale-tier swap

    @classmethod
    def evaluate_token(
        cls,
        mint: str,
        symbol: str,
        swaps: List[RealSwapRecord],
        pool_liquidity_usd: Optional[float] = None
    ) -> RelativeWhaleMetrics:
        """
        Calculates continuous Relative Whale Strength for a token.
        When no verified whale swaps exist, underlying metrics remain None (UNKNOWN).
        Only strictly verified quotes participate in whale calculations.
        """
        if not swaps:
            return RelativeWhaleMetrics(
                mint=mint,
                symbol=symbol,
                pool_liquidity_usd=pool_liquidity_usd,
                absolute_netflow_usd=None,
                flow_to_liquidity_ratio=None,
                largest_single_buy_usd=None,
                single_order_pool_impact_pct=None,
                accumulating_whales_count=0,
                accumulation_events_count=0,
                whale_buy_acceleration=None,
                relative_whale_strength_score=50.0,
                conviction_tier="NEUTRAL",
                quote_quality=1.0,
                provenance=Provenance(source_type=SourceType.REAL, confidence=0.5)
            )

        strictly_verified_swaps = [s for s in swaps if is_swap_quote_verified(s)]
        quote_quality = len(strictly_verified_swaps) / max(len(swaps), 1)

        whale_swaps = [s for s in strictly_verified_swaps if s.quote_amount_usd >= cls.WHALE_SWAP_MIN_USD]

        if not whale_swaps:
            return RelativeWhaleMetrics(
                mint=mint,
                symbol=symbol,
                pool_liquidity_usd=pool_liquidity_usd,
                absolute_netflow_usd=None,
                flow_to_liquidity_ratio=None,
                largest_single_buy_usd=None,
                single_order_pool_impact_pct=None,
                accumulating_whales_count=0,
                accumulation_events_count=0,
                whale_buy_acceleration=None,
                relative_whale_strength_score=50.0,
                conviction_tier="NEUTRAL",
                quote_quality=round(quote_quality, 4),
                provenance=Provenance(source_type=SourceType.REAL, confidence=round(quote_quality * 0.7, 2))
            )

        whale_buys = [s for s in whale_swaps if s.side == "BUY"]
        whale_sells = [s for s in whale_swaps if s.side == "SELL"]

        buy_vol = sum(s.quote_amount_usd for s in whale_buys)
        sell_vol = sum(s.quote_amount_usd for s in whale_sells)
        netflow = buy_vol - sell_vol

        largest_buy = max([s.quote_amount_usd for s in whale_buys]) if whale_buys else None

        if pool_liquidity_usd is not None and pool_liquidity_usd > 0:
            flow_to_liq = netflow / pool_liquidity_usd
            single_order_impact_pct = ((largest_buy / pool_liquidity_usd) * 100.0) if largest_buy is not None else 0.0
            # 1. Flow / Liquidity ratio (30%) -> 1.0% of pool is 100 pts
            rel_flow_score = min(max(flow_to_liq * 100.0 * 50.0, 0.0), 100.0) if netflow > 0 else 0.0
            # 2. Single-order pool impact (25%) -> 0.5% single buy is 100 pts
            impact_score = min(max(single_order_impact_pct * 200.0, 0.0), 100.0)
        else:
            flow_to_liq = None
            single_order_impact_pct = None
            rel_flow_score = 50.0  # Neutral fallback without guessing $1M
            impact_score = 50.0    # Neutral fallback without guessing $1M

        accum_wallets = set(s.wallet for s in whale_buys)
        accum_events = len(whale_buys)

        # Acceleration: volume in 2nd half vs 1st half
        if len(whale_buys) >= 2:
            mid = len(whale_buys) // 2
            v1 = sum(s.quote_amount_usd for s in whale_buys[:mid])
            v2 = sum(s.quote_amount_usd for s in whale_buys[mid:])
            accel = (v2 - v1) / max(v1, 1.0)
        else:
            accel = None

        # 3. Accumulation events / repeat buys (20%)
        events_score = min(accum_events * 25.0, 100.0)
        # 4. Number of distinct whale wallets (15%)
        wallets_score = min(len(accum_wallets) * 33.3, 100.0)
        # 5. Buy acceleration (10%)
        accel_score = min(max(((accel if accel is not None else 0.0) + 0.5) * 50.0, 0.0), 100.0)

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
            flow_to_liquidity_ratio=round(flow_to_liq, 6) if flow_to_liq is not None else None,
            largest_single_buy_usd=round(largest_buy, 2) if largest_buy is not None else None,
            single_order_pool_impact_pct=round(single_order_impact_pct, 4) if single_order_impact_pct is not None else None,
            accumulating_whales_count=len(accum_wallets),
            accumulation_events_count=accum_events,
            whale_buy_acceleration=round(accel, 2) if accel is not None else None,
            relative_whale_strength_score=composite_score,
            conviction_tier=tier,
            quote_quality=round(quote_quality, 4),
            provenance=Provenance(
                source_type=SourceType.REAL,
                confidence=round(quote_quality if pool_liquidity_usd is not None else (quote_quality * 0.6), 2),
                verified_on_chain=True
            )
        )
