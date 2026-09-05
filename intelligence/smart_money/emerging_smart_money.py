"""
Emerging Smart Money Intelligence Engine.
Identifies early accumulation, order size escalation, and smart wallet behavior
strictly from observed within-run transaction telemetry (cold start).
Does NOT use historical pre-seeded reputations.
Zero fallback to default $1,000,000 pool liquidity.
Zero conversion of unknown USD quotes to 0.0.
Strict UNKNOWN (None) vs REAL ZERO (0.0) semantic integrity.
"""

from dataclasses import dataclass, field
import logging
import time
from typing import Any, Dict, List, Optional

from blockchain.parsers.real_swap_parser import RealSwapRecord
from blockchain.solana.types import Provenance, SourceType

logger = logging.getLogger("meme_alpha_hunter.emerging_smart_money")


@dataclass
class EmergingWalletProfile:
    wallet_pubkey: str
    swap_count: int = 0
    verified_quote_swaps: int = 0
    unverified_quote_swaps: int = 0
    buy_count: int = 0
    sell_count: int = 0
    buy_volume_usd: Optional[float] = None
    sell_volume_usd: Optional[float] = None
    netflow_usd: Optional[float] = None
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    avg_trade_size_usd: Optional[float] = None
    largest_trade_usd: Optional[float] = None
    consecutive_buys: int = 0
    buy_acceleration: Optional[float] = None  # Order size scaling
    sell_ratio: Optional[float] = None       # Sell volume / Total volume
    holding_time_sec: float = 0.0
    tokens_traded: set = field(default_factory=set)
    pools_traded: set = field(default_factory=set)
    max_pool_impact_pct: Optional[float] = None
    emerging_smart_money_score: float = 50.0 # 0 to 100
    is_emerging_smart_money: bool = False
    liquidity_fallback_count: int = 0
    unknown_quotes_count: int = 0


@dataclass
class TokenEmergingSmartMoneySignal:
    mint: str
    symbol: str
    emerging_smart_score: float  # 0 to 100
    emerging_netflow_usd: Optional[float]
    accumulating_wallets_count: int
    distributing_wallets_count: int
    total_emerging_volume_usd: Optional[float]
    quote_quality: float  # 0.0 to 1.0 (ratio of verified quote swaps)
    signal_label: str  # "HIGH_CONVICTION_ACCUMULATION", "MODERATE_ACCUMULATION", "NEUTRAL", "DISTRIBUTION"
    provenance: Provenance = field(default_factory=Provenance)


class EmergingSmartMoneyEngine:
    EMERGING_THRESHOLD = 70.0 # Score to qualify as Emerging Smart Money

    def __init__(self):
        self.wallets: Dict[str, EmergingWalletProfile] = {}
        self.token_swaps: Dict[str, List[RealSwapRecord]] = {}

    def process_swap(self, swap: RealSwapRecord, pool_liquidity_usd: Optional[float] = None) -> EmergingWalletProfile:
        """
        Updates emerging wallet profile dynamically from a real swap.
        Does NOT convert unknown quotes to 0.0.
        Does NOT substitute default $1,000,000 for pool liquidity.
        """
        w = swap.wallet
        mint = swap.mint

        if w not in self.wallets:
            self.wallets[w] = EmergingWalletProfile(
                wallet_pubkey=w,
                first_seen=swap.timestamp,
                last_seen=swap.timestamp
            )

        p = self.wallets[w]
        p.last_seen = swap.timestamp
        p.swap_count += 1
        p.tokens_traded.add(mint)
        p.pools_traded.add(swap.pool)

        usd = swap.quote_amount_usd

        if usd is None:
            # Quote is unknown: do NOT contribute to volume stats as 0.0
            p.unverified_quote_swaps += 1
            p.unknown_quotes_count += 1
            if swap.side == "BUY":
                p.buy_count += 1
                p.consecutive_buys += 1
            else:
                p.sell_count += 1
                p.consecutive_buys = 0
        else:
            p.verified_quote_swaps += 1
            if swap.side == "BUY":
                p.buy_count += 1
                p.buy_volume_usd = (p.buy_volume_usd if p.buy_volume_usd is not None else 0.0) + usd
                p.consecutive_buys += 1
            else:
                p.sell_count += 1
                p.sell_volume_usd = (p.sell_volume_usd if p.sell_volume_usd is not None else 0.0) + usd
                p.consecutive_buys = 0

            b_vol = p.buy_volume_usd if p.buy_volume_usd is not None else 0.0
            s_vol = p.sell_volume_usd if p.sell_volume_usd is not None else 0.0
            p.netflow_usd = b_vol - s_vol
            total_vol = b_vol + s_vol
            p.sell_ratio = s_vol / max(total_vol, 1.0)
            p.avg_trade_size_usd = total_vol / max(p.verified_quote_swaps, 1)
            p.largest_trade_usd = max(p.largest_trade_usd if p.largest_trade_usd is not None else 0.0, usd)

            if pool_liquidity_usd is not None and pool_liquidity_usd > 0:
                impact = (usd / pool_liquidity_usd) * 100.0
                p.max_pool_impact_pct = max(p.max_pool_impact_pct if p.max_pool_impact_pct is not None else 0.0, impact)
            else:
                # Pool liquidity is unknown: keep as None (UNKNOWN)
                pass

            if p.avg_trade_size_usd and p.avg_trade_size_usd > 0 and p.largest_trade_usd is not None:
                p.buy_acceleration = (p.largest_trade_usd - p.avg_trade_size_usd) / p.avg_trade_size_usd

        # Compute Emerging Smart Money Score
        consec_score = min(p.consecutive_buys * 20.0, 100.0)

        if p.netflow_usd is not None:
            netflow_score = min(max(p.netflow_usd / 250.0, 0.0), 100.0) if p.netflow_usd > 0 else 0.0
        else:
            netflow_score = 50.0  # Neutral when volume is unverified

        if p.buy_acceleration is not None:
            accel_score = min(max((p.buy_acceleration + 0.5) * 50.0, 0.0), 100.0)
        else:
            accel_score = 50.0  # Neutral

        if p.sell_ratio is not None:
            sell_pres_score = max(0.0, (1.0 - p.sell_ratio) * 100.0)
        else:
            sell_pres_score = 50.0  # Neutral

        if p.max_pool_impact_pct is not None:
            impact_score = min(p.max_pool_impact_pct * 100.0, 100.0)
        else:
            impact_score = 50.0  # Neutral when pool liquidity is unknown (never $1M)

        p.emerging_smart_money_score = round(
            (consec_score * 0.30) +
            (netflow_score * 0.25) +
            (accel_score * 0.20) +
            (sell_pres_score * 0.15) +
            (impact_score * 0.10),
            1
        )
        p.is_emerging_smart_money = p.emerging_smart_money_score >= self.EMERGING_THRESHOLD

        if mint not in self.token_swaps:
            self.token_swaps[mint] = []
        self.token_swaps[mint].append(swap)

        return p

    def evaluate_token_signal(self, mint: str, symbol: str = "UNKNOWN") -> TokenEmergingSmartMoneySignal:
        """
        Calculates aggregate Token Emerging Smart Money Signal.
        """
        swaps = self.token_swaps.get(mint, [])
        if not swaps:
            return TokenEmergingSmartMoneySignal(
                mint=mint,
                symbol=symbol,
                emerging_smart_score=50.0,
                emerging_netflow_usd=None,
                accumulating_wallets_count=0,
                distributing_wallets_count=0,
                total_emerging_volume_usd=None,
                quote_quality=1.0,
                signal_label="NEUTRAL",
                provenance=Provenance(source_type=SourceType.REAL, confidence=0.5)
            )

        verified_swaps = [s for s in swaps if s.quote_amount_usd is not None]
        quote_quality = len(verified_swaps) / max(len(swaps), 1)

        accumulators = set()
        distributors = set()
        emerging_buy_vol = 0.0
        emerging_sell_vol = 0.0
        emerging_scores = []
        has_verified_emerging_trades = False

        for s in swaps:
            p = self.wallets.get(s.wallet)
            if p and p.is_emerging_smart_money:
                emerging_scores.append(p.emerging_smart_money_score)
                if s.quote_amount_usd is not None:
                    has_verified_emerging_trades = True
                    usd = s.quote_amount_usd
                    if s.side == "BUY":
                        accumulators.add(s.wallet)
                        emerging_buy_vol += usd
                    else:
                        distributors.add(s.wallet)
                        emerging_sell_vol += usd
                else:
                    if s.side == "BUY":
                        accumulators.add(s.wallet)
                    else:
                        distributors.add(s.wallet)

        netflow = (emerging_buy_vol - emerging_sell_vol) if has_verified_emerging_trades else None
        total_vol = (emerging_buy_vol + emerging_sell_vol) if has_verified_emerging_trades else None
        avg_score = (sum(emerging_scores) / len(emerging_scores)) if emerging_scores else 50.0

        if netflow is not None and netflow >= 5_000.0 and len(accumulators) >= 2:
            token_score = min(avg_score + 15.0, 98.0)
            label = "HIGH_CONVICTION_ACCUMULATION"
        elif netflow is not None and netflow >= 1_000.0:
            token_score = min(avg_score + 8.0, 92.0)
            label = "MODERATE_ACCUMULATION"
        elif netflow is not None and netflow <= -5_000.0:
            token_score = max(avg_score - 25.0, 10.0)
            label = "DISTRIBUTION"
        else:
            token_score = avg_score
            label = "NEUTRAL"

        return TokenEmergingSmartMoneySignal(
            mint=mint,
            symbol=symbol,
            emerging_smart_score=round(token_score, 1),
            emerging_netflow_usd=round(netflow, 2) if netflow is not None else None,
            accumulating_wallets_count=len(accumulators),
            distributing_wallets_count=len(distributors),
            total_emerging_volume_usd=round(total_vol, 2) if total_vol is not None else None,
            quote_quality=round(quote_quality, 4),
            signal_label=label,
            provenance=Provenance(source_type=SourceType.REAL, confidence=quote_quality, verified_on_chain=True)
        )
