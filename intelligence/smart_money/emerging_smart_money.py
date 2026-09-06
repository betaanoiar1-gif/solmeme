"""
Emerging Smart Money Intelligence Engine.
Identifies early accumulation, order-size escalation, breadth, and recency
strictly from observed real Solana transaction telemetry.

Design goals:
- no historical pre-seeded reputations in live mode
- no synthetic/default liquidity values
- strictly verified USD quotes for USD analytics
- no duplicate processing when the same recent swap is observed again
- distinguish lack of evidence from real neutral evidence
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from blockchain.parsers.real_swap_parser import RealSwapRecord
from blockchain.solana.types import Provenance, SourceType


def is_swap_quote_verified(swap: RealSwapRecord) -> bool:
    """Return True only for a real, on-chain-verified USD quote."""
    if swap.quote_amount_usd is None:
        return False
    if not getattr(swap, "is_quote_verified", False):
        return False
    prov = getattr(swap, "provenance", None)
    if prov is None:
        return False
    if not getattr(prov, "verified_on_chain", False):
        return False
    if getattr(prov, "source_type", SourceType.UNKNOWN) != SourceType.REAL:
        return False
    if hasattr(prov, "rpc_verified") and getattr(prov, "rpc_verified") is False:
        return False
    return True


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
    first_seen: Optional[float] = None
    last_seen: Optional[float] = None
    avg_trade_size_usd: Optional[float] = None
    largest_trade_usd: Optional[float] = None
    consecutive_buys: int = 0
    buy_acceleration: Optional[float] = None
    sell_ratio: Optional[float] = None
    holding_time_sec: float = 0.0
    tokens_traded: set = field(default_factory=set)
    pools_traded: set = field(default_factory=set)
    max_pool_impact_pct: Optional[float] = None
    emerging_smart_money_score: float = 50.0
    is_emerging_smart_money: bool = False
    liquidity_fallback_count: int = 0
    unknown_quotes_count: int = 0


@dataclass
class TokenEmergingSmartMoneySignal:
    mint: str
    symbol: str
    emerging_smart_score: float
    emerging_netflow_usd: Optional[float]
    accumulating_wallets_count: int
    distributing_wallets_count: int
    total_emerging_volume_usd: Optional[float]
    quote_quality: float
    signal_label: str
    provenance: Provenance = field(default_factory=Provenance)


class EmergingSmartMoneyEngine:
    """Cold-start, duplicate-safe emerging-money detector."""

    EMERGING_THRESHOLD = 70.0
    MIN_VERIFIED_SWAPS_FOR_EMERGING = 2
    ACCUMULATOR_MIN_BUY_SHARE = 0.60
    ACCUMULATOR_MAX_SELL_RATIO = 0.40
    RECENT_WINDOW_SEC = 300.0

    def __init__(self):
        self.wallets: Dict[str, EmergingWalletProfile] = {}
        self.token_swaps: Dict[str, List[RealSwapRecord]] = {}
        self.processed_signatures: Set[str] = set()

    def process_swap(
        self,
        swap: RealSwapRecord,
        pool_liquidity_usd: Optional[float] = None,
    ) -> EmergingWalletProfile:
        """Update one unique real swap; repeated signatures are ignored."""
        signature = getattr(swap, "signature", None)
        if signature and signature in self.processed_signatures:
            existing = self.wallets.get(swap.wallet)
            if existing is not None:
                return existing
        if signature:
            self.processed_signatures.add(signature)

        w = swap.wallet
        mint = swap.mint
        if w not in self.wallets:
            self.wallets[w] = EmergingWalletProfile(
                wallet_pubkey=w,
                first_seen=swap.timestamp,
                last_seen=swap.timestamp,
            )

        p = self.wallets[w]
        p.last_seen = swap.timestamp
        p.swap_count += 1
        p.tokens_traded.add(mint)
        p.pools_traded.add(swap.pool)

        verified = is_swap_quote_verified(swap)
        if not verified:
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
            usd = float(swap.quote_amount_usd)
            if swap.side == "BUY":
                p.buy_count += 1
                p.buy_volume_usd = (p.buy_volume_usd or 0.0) + usd
                p.consecutive_buys += 1
            else:
                p.sell_count += 1
                p.sell_volume_usd = (p.sell_volume_usd or 0.0) + usd
                p.consecutive_buys = 0

            buy_vol = p.buy_volume_usd or 0.0
            sell_vol = p.sell_volume_usd or 0.0
            total_vol = buy_vol + sell_vol
            p.netflow_usd = buy_vol - sell_vol
            p.sell_ratio = sell_vol / total_vol if total_vol > 0 else None
            p.avg_trade_size_usd = total_vol / p.verified_quote_swaps
            p.largest_trade_usd = max(p.largest_trade_usd or 0.0, usd)

            if pool_liquidity_usd is not None and pool_liquidity_usd > 0:
                impact = (usd / pool_liquidity_usd) * 100.0
                p.max_pool_impact_pct = max(p.max_pool_impact_pct or 0.0, impact)

            if p.avg_trade_size_usd and p.avg_trade_size_usd > 0 and p.largest_trade_usd is not None:
                p.buy_acceleration = max(
                    (p.largest_trade_usd - p.avg_trade_size_usd) / p.avg_trade_size_usd,
                    0.0,
                )

        self._refresh_wallet_score(p)

        if mint not in self.token_swaps:
            self.token_swaps[mint] = []
        self.token_swaps[mint].append(swap)
        return p

    def _refresh_wallet_score(self, p: EmergingWalletProfile) -> None:
        """Score only what is actually observed; do not invent missing components."""
        if p.verified_quote_swaps < self.MIN_VERIFIED_SWAPS_FOR_EMERGING:
            p.emerging_smart_money_score = 50.0
            p.is_emerging_smart_money = False
            return

        buy_vol = p.buy_volume_usd or 0.0
        sell_vol = p.sell_volume_usd or 0.0
        total_vol = buy_vol + sell_vol
        if total_vol <= 0:
            p.emerging_smart_money_score = 50.0
            p.is_emerging_smart_money = False
            return

        buy_pressure = buy_vol / total_vol
        netflow_ratio = max(min((buy_vol - sell_vol) / total_vol, 1.0), -1.0)
        netflow_score = (netflow_ratio + 1.0) * 50.0
        buy_pressure_score = buy_pressure * 100.0
        consecutive_score = min(p.consecutive_buys / 4.0, 1.0) * 100.0
        accel_score = min(max(p.buy_acceleration or 0.0, 0.0) / 2.0, 1.0) * 100.0

        if p.max_pool_impact_pct is not None:
            impact_score = min(max(p.max_pool_impact_pct, 0.0) / 1.0, 1.0) * 100.0
        else:
            impact_score = None

        components = [
            (buy_pressure_score, 0.30),
            (netflow_score, 0.25),
            (consecutive_score, 0.15),
            (accel_score, 0.15),
        ]
        if impact_score is not None:
            components.append((impact_score, 0.15))
        else:
            # Redistribute only the observed weights; no neutral filler.
            components = [
                (buy_pressure_score, 0.30 / 0.85),
                (netflow_score, 0.25 / 0.85),
                (consecutive_score, 0.15 / 0.85),
                (accel_score, 0.15 / 0.85),
            ]

        score = sum(value * weight for value, weight in components)
        p.emerging_smart_money_score = round(min(max(score, 0.0), 99.0), 1)
        p.is_emerging_smart_money = (
            p.emerging_smart_money_score >= self.EMERGING_THRESHOLD
            and buy_pressure >= self.ACCUMULATOR_MIN_BUY_SHARE
            and (p.sell_ratio is None or p.sell_ratio <= self.ACCUMULATOR_MAX_SELL_RATIO)
        )

    def _is_accumulating_wallet(self, p: EmergingWalletProfile) -> bool:
        if p.verified_quote_swaps < self.MIN_VERIFIED_SWAPS_FOR_EMERGING:
            return False
        buy_vol = p.buy_volume_usd or 0.0
        sell_vol = p.sell_volume_usd or 0.0
        total = buy_vol + sell_vol
        if total <= 0:
            return False
        buy_share = buy_vol / total
        sell_ratio = sell_vol / total
        return buy_share >= self.ACCUMULATOR_MIN_BUY_SHARE and sell_ratio <= self.ACCUMULATOR_MAX_SELL_RATIO and buy_vol > sell_vol

    def evaluate_token_signal(
        self,
        mint: str,
        symbol: str = "UNKNOWN",
    ) -> TokenEmergingSmartMoneySignal:
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
                quote_quality=0.0,
                signal_label="NEUTRAL",
                provenance=Provenance(source_type=SourceType.REAL, confidence=0.0),
            )

        verified_swaps = [s for s in swaps if is_swap_quote_verified(s)]
        quote_quality = len(verified_swaps) / len(swaps) if swaps else 0.0

        accumulators: Dict[str, EmergingWalletProfile] = {}
        distributors: Set[str] = set()
        latest_ts: Optional[float] = None
        for s in verified_swaps:
            if s.timestamp is not None:
                latest_ts = max(latest_ts, float(s.timestamp)) if latest_ts is not None else float(s.timestamp)
            profile = self.wallets.get(s.wallet)
            if profile is None:
                continue
            if self._is_accumulating_wallet(profile):
                accumulators[s.wallet] = profile
            elif profile.verified_quote_swaps >= self.MIN_VERIFIED_SWAPS_FOR_EMERGING:
                buy_vol = profile.buy_volume_usd or 0.0
                sell_vol = profile.sell_volume_usd or 0.0
                if sell_vol > buy_vol:
                    distributors.add(s.wallet)

        buy_vol = 0.0
        sell_vol = 0.0
        recent_buy_vol = 0.0
        total_emerging_scores: List[float] = []
        for wallet, profile in accumulators.items():
            buy_vol += profile.buy_volume_usd or 0.0
            sell_vol += profile.sell_volume_usd or 0.0
            total_emerging_scores.append(profile.emerging_smart_money_score)
            if latest_ts is not None:
                for s in swaps:
                    if s.wallet == wallet and is_swap_quote_verified(s) and s.side == "BUY" and s.timestamp is not None and latest_ts - float(s.timestamp) <= self.RECENT_WINDOW_SEC:
                        recent_buy_vol += float(s.quote_amount_usd)

        emerging_netflow = buy_vol - sell_vol if accumulators else None
        emerging_total = buy_vol + sell_vol if accumulators else None

        if not accumulators or emerging_total is None or emerging_total <= 0:
            # Real verified flow exists, but not enough breadth/imbalance to call accumulation.
            score = 50.0
            if verified_swaps:
                total_buy = sum(float(s.quote_amount_usd) for s in verified_swaps if s.side == "BUY")
                total_sell = sum(float(s.quote_amount_usd) for s in verified_swaps if s.side == "SELL")
                total = total_buy + total_sell
                if total > 0:
                    score = round(50.0 + ((total_buy / total) - 0.5) * 40.0, 1)
            label = "DISTRIBUTION" if emerging_netflow is not None and emerging_netflow < 0 else "NEUTRAL"
            return TokenEmergingSmartMoneySignal(
                mint=mint,
                symbol=symbol,
                emerging_smart_score=score,
                emerging_netflow_usd=emerging_netflow,
                accumulating_wallets_count=0,
                distributing_wallets_count=len(distributors),
                total_emerging_volume_usd=emerging_total,
                quote_quality=round(quote_quality, 4),
                signal_label=label,
                provenance=Provenance(source_type=SourceType.REAL, timestamp=latest_ts, confidence=round(quote_quality, 4), verified_on_chain=True),
            )

        buy_pressure_score = (buy_vol / emerging_total) * 100.0
        netflow_ratio = max(min(emerging_netflow / emerging_total, 1.0), -1.0)
        netflow_score = (netflow_ratio + 1.0) * 50.0
        breadth_score = min(len(accumulators) / 3.0, 1.0) * 100.0
        wallet_score = sum(total_emerging_scores) / len(total_emerging_scores) if total_emerging_scores else 50.0
        recency_score = min(max(recent_buy_vol / buy_vol, 0.0), 1.0) * 100.0 if buy_vol > 0 else 0.0

        token_score = round(
            (buy_pressure_score * 0.25)
            + (netflow_score * 0.25)
            + (breadth_score * 0.20)
            + (recency_score * 0.15)
            + (wallet_score * 0.15),
            1,
        )

        if emerging_netflow < 0:
            label = "DISTRIBUTION"
        elif token_score >= 75.0 and len(accumulators) >= 2 and quote_quality >= 0.80:
            label = "HIGH_CONVICTION_ACCUMULATION"
        elif token_score >= 65.0 and emerging_netflow > 0:
            label = "MODERATE_ACCUMULATION"
        else:
            label = "NEUTRAL"

        return TokenEmergingSmartMoneySignal(
            mint=mint,
            symbol=symbol,
            emerging_smart_score=token_score,
            emerging_netflow_usd=round(emerging_netflow, 2),
            accumulating_wallets_count=len(accumulators),
            distributing_wallets_count=len(distributors),
            total_emerging_volume_usd=round(emerging_total, 2),
            quote_quality=round(quote_quality, 4),
            signal_label=label,
            provenance=Provenance(
                source_type=SourceType.REAL,
                timestamp=latest_ts,
                confidence=round(quote_quality, 4),
                verified_on_chain=True,
            ),
        )
