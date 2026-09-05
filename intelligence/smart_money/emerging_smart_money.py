"""
Emerging Smart Money Intelligence Engine.
Identifies early accumulation, order size escalation, and smart wallet behavior
strictly from observed within-run transaction telemetry (cold start).
Does NOT use historical pre-seeded reputations.
Works alongside ProvenSmartMoneyEngine without altering existing logic.
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
    buy_count: int = 0
    sell_count: int = 0
    buy_volume_usd: float = 0.0
    sell_volume_usd: float = 0.0
    netflow_usd: float = 0.0
    first_seen: float = field(default_factory=time.time)
    last_seen: float = field(default_factory=time.time)
    avg_trade_size_usd: float = 0.0
    largest_trade_usd: float = 0.0
    consecutive_buys: int = 0
    buy_acceleration: float = 0.0  # Order size scaling
    sell_ratio: float = 0.0       # Sell volume / Total volume
    holding_time_sec: float = 0.0
    tokens_traded: set = field(default_factory=set)
    pools_traded: set = field(default_factory=set)
    max_pool_impact_pct: float = 0.0
    emerging_smart_money_score: float = 50.0 # 0 to 100
    is_emerging_smart_money: bool = False


@dataclass
class TokenEmergingSmartMoneySignal:
    mint: str
    symbol: str
    emerging_smart_score: float  # 0 to 100
    emerging_netflow_usd: float
    accumulating_wallets_count: int
    distributing_wallets_count: int
    total_emerging_volume_usd: float
    signal_label: str  # "HIGH_CONVICTION_ACCUMULATION", "MODERATE_ACCUMULATION", "NEUTRAL", "DISTRIBUTION"
    provenance: Provenance = field(default_factory=Provenance)


class EmergingSmartMoneyEngine:
    EMERGING_THRESHOLD = 70.0 # Score to qualify as Emerging Smart Money

    def __init__(self):
        self.wallets: Dict[str, EmergingWalletProfile] = {}
        self.token_swaps: Dict[str, List[RealSwapRecord]] = {}

    def process_swap(self, swap: RealSwapRecord, pool_liquidity_usd: float = 1_000_000.0) -> EmergingWalletProfile:
        """
        Updates emerging wallet profile dynamically from a real swap.
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

        usd = swap.quote_amount_usd or 0.0

        if swap.side == "BUY":
            p.buy_count += 1
            p.buy_volume_usd += usd
            p.consecutive_buys += 1
        else:
            p.sell_count += 1
            p.sell_volume_usd += usd
            p.consecutive_buys = 0

        p.netflow_usd = p.buy_volume_usd - p.sell_volume_usd
        total_vol = p.buy_volume_usd + p.sell_volume_usd
        p.sell_ratio = p.sell_volume_usd / max(total_vol, 1.0)
        p.avg_trade_size_usd = total_vol / max(p.swap_count, 1)
        p.largest_trade_usd = max(p.largest_trade_usd, usd)

        impact = (usd / max(pool_liquidity_usd, 1.0)) * 100.0
        p.max_pool_impact_pct = max(p.max_pool_impact_pct, impact)

        # Compute buy acceleration (largest vs average order scaling)
        p.buy_acceleration = (p.largest_trade_usd - p.avg_trade_size_usd) / max(p.avg_trade_size_usd, 1.0)

        # Compute Emerging Smart Money Score
        # Accumulation consistency (30%) + Netflow scale (25%) + Size acceleration (20%) + Low sell pressure (15%) + Pool impact (10%)
        consec_score = min(p.consecutive_buys * 20.0, 100.0)
        netflow_score = min(max(p.netflow_usd / 250.0, 0.0), 100.0) if p.netflow_usd > 0 else 0.0
        accel_score = min(max((p.buy_acceleration + 0.5) * 50.0, 0.0), 100.0)
        sell_pres_score = max(0.0, (1.0 - p.sell_ratio) * 100.0)
        impact_score = min(p.max_pool_impact_pct * 100.0, 100.0)

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
                emerging_netflow_usd=0.0,
                accumulating_wallets_count=0,
                distributing_wallets_count=0,
                total_emerging_volume_usd=0.0,
                signal_label="NEUTRAL",
                provenance=Provenance(source_type=SourceType.REAL, confidence=0.5)
            )

        accumulators = set()
        distributors = set()
        emerging_buy_vol = 0.0
        emerging_sell_vol = 0.0
        emerging_scores = []

        for s in swaps:
            p = self.wallets.get(s.wallet)
            if p and p.is_emerging_smart_money:
                emerging_scores.append(p.emerging_smart_money_score)
                usd = s.quote_amount_usd or 0.0
                if s.side == "BUY":
                    accumulators.add(s.wallet)
                    emerging_buy_vol += usd
                else:
                    distributors.add(s.wallet)
                    emerging_sell_vol += usd

        netflow = emerging_buy_vol - emerging_sell_vol
        total_vol = emerging_buy_vol + emerging_sell_vol
        avg_score = (sum(emerging_scores) / len(emerging_scores)) if emerging_scores else 50.0

        if netflow >= 5_000.0 and len(accumulators) >= 2:
            token_score = min(avg_score + 15.0, 98.0)
            label = "HIGH_CONVICTION_ACCUMULATION"
        elif netflow >= 1_000.0:
            token_score = min(avg_score + 8.0, 92.0)
            label = "MODERATE_ACCUMULATION"
        elif netflow <= -5_000.0:
            token_score = max(avg_score - 25.0, 10.0)
            label = "DISTRIBUTION"
        else:
            token_score = avg_score
            label = "NEUTRAL"

        return TokenEmergingSmartMoneySignal(
            mint=mint,
            symbol=symbol,
            emerging_smart_score=round(token_score, 1),
            emerging_netflow_usd=round(netflow, 2),
            accumulating_wallets_count=len(accumulators),
            distributing_wallets_count=len(distributors),
            total_emerging_volume_usd=round(total_vol, 2),
            signal_label=label,
            provenance=Provenance(source_type=SourceType.REAL, confidence=1.0, verified_on_chain=True)
        )
