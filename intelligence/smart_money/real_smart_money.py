"""
Real Smart Money Intelligence Engine for Solana.
Builds wallet reputations dynamically from observed on-chain transactions:
win rate, earlyness timing, trade size, and realized profitability.
Adds an evidence-gated emerging smart-money layer for cold-start live runs.
Zero hardcoded scores in live mode.
"""

from dataclasses import dataclass, field
import logging
import time
from typing import Any, Dict, List, Optional

from app.core.database import DatabaseManager
from blockchain.parsers.real_swap_parser import RealSwapRecord
from blockchain.solana.types import Provenance, SourceType
from intelligence.smart_money.emerging_smart_money import (
    EmergingSmartMoneyEngine,
    is_swap_quote_verified,
)

logger = logging.getLogger("meme_alpha_hunter.real_smart_money")


@dataclass
class WalletTradeRecord:
    mint: str
    entry_time: Optional[float]
    entry_price: float
    entry_usd: float
    exit_time: Optional[float] = None
    exit_price: Optional[float] = None
    exit_usd: Optional[float] = None
    realized_pnl_usd: float = 0.0
    is_closed: bool = False


@dataclass
class WalletProfile:
    address: str
    total_trades_count: int = 0
    winning_trades_count: int = 0
    losing_trades_count: int = 0
    total_volume_usd: float = 0.0
    total_realized_pnl_usd: float = 0.0
    avg_earlyness_score: float = 50.0
    smart_wallet_score: float = 50.0
    is_smart_money: bool = False
    first_seen: Optional[float] = None
    last_seen: Optional[float] = None
    trades: List[WalletTradeRecord] = field(default_factory=list)


@dataclass
class TokenSmartMoneySignal:
    mint: str
    smart_money_score: float
    netflow_usd: float
    smart_buyers_count: int
    smart_sellers_count: int
    total_smart_volume_usd: float
    signal_label: str
    provenance: Provenance = field(default_factory=Provenance)
    emerging_smart_money_score: Optional[float] = None
    emerging_netflow_usd: Optional[float] = None
    emerging_accumulating_wallets: int = 0
    emerging_distributing_wallets: int = 0
    emerging_quote_quality: Optional[float] = None
    emerging_signal_label: str = "NEUTRAL"


class RealSmartMoneyEngine:
    SMART_MONEY_THRESHOLD = 70.0

    def __init__(self, db: Optional[DatabaseManager] = None):
        self.db = db or DatabaseManager()
        self.wallets: Dict[str, WalletProfile] = {}
        self.token_swaps: Dict[str, List[RealSwapRecord]] = {}
        # Cold-start detector: learns from the current run without seeded reputation.
        self.emerging_engine = EmergingSmartMoneyEngine()

    def process_real_swap(
        self,
        swap: RealSwapRecord,
        token_first_seen: Optional[float] = None,
        pool_liquidity_usd: Optional[float] = None,
    ) -> WalletProfile:
        """Update both historical-style and cold-start smart-money models from one real swap."""
        wallet_addr = swap.wallet
        mint = swap.mint

        if wallet_addr not in self.wallets:
            self.wallets[wallet_addr] = WalletProfile(
                address=wallet_addr,
                first_seen=swap.timestamp,
            )

        profile = self.wallets[wallet_addr]
        profile.last_seen = swap.timestamp
        if swap.is_quote_verified and swap.quote_amount_usd is not None:
            profile.total_volume_usd += swap.quote_amount_usd

        if mint not in self.token_swaps:
            self.token_swaps[mint] = []
        self.token_swaps[mint].append(swap)

        # The emerging model is intentionally fed every observed swap. Its USD
        # analytics are internally gated to strictly verified quotes.
        self.emerging_engine.process_swap(
            swap,
            pool_liquidity_usd=pool_liquidity_usd,
        )

        earlyness = 50.0
        if (
            token_first_seen is not None
            and token_first_seen > 0
            and swap.timestamp is not None
            and swap.side == "BUY"
        ):
            age_min = max((swap.timestamp - token_first_seen) / 60.0, 0.0)
            if age_min <= 15.0:
                earlyness = 95.0
            elif age_min <= 60.0:
                earlyness = 80.0
            elif age_min <= 240.0:
                earlyness = 60.0
            else:
                earlyness = 40.0

        if (
            swap.is_quote_verified
            and swap.side == "BUY"
            and swap.quote_amount_usd is not None
            and swap.price_usd is not None
        ):
            profile.trades.append(
                WalletTradeRecord(
                    mint=mint,
                    entry_time=swap.timestamp,
                    entry_price=swap.price_usd,
                    entry_usd=swap.quote_amount_usd,
                )
            )
        elif (
            swap.is_quote_verified
            and swap.side == "SELL"
            and swap.quote_amount_usd is not None
            and swap.price_usd is not None
        ):
            open_buys = [t for t in profile.trades if t.mint == mint and not t.is_closed]
            if open_buys:
                buy_trade = open_buys[0]
                buy_trade.exit_time = swap.timestamp
                buy_trade.exit_price = swap.price_usd
                buy_trade.exit_usd = swap.quote_amount_usd
                buy_trade.is_closed = True

                pnl = buy_trade.exit_usd - buy_trade.entry_usd
                buy_trade.realized_pnl_usd = pnl
                profile.total_realized_pnl_usd += pnl
                profile.total_trades_count += 1
                if pnl > 0:
                    profile.winning_trades_count += 1
                else:
                    profile.losing_trades_count += 1

        profile.smart_wallet_score = self._compute_wallet_score(profile, earlyness)
        profile.is_smart_money = profile.smart_wallet_score >= self.SMART_MONEY_THRESHOLD
        return profile

    def _compute_wallet_score(self, profile: WalletProfile, latest_earlyness: float) -> float:
        """Compute the reputation score from observed wallet history."""
        if profile.total_trades_count == 0:
            return round((latest_earlyness * 0.5) + 25.0, 2)

        win_rate = (profile.winning_trades_count / profile.total_trades_count) * 100.0

        if profile.total_realized_pnl_usd > 10_000.0:
            pnl_factor = 95.0
        elif profile.total_realized_pnl_usd > 1_000.0:
            pnl_factor = 80.0
        elif profile.total_realized_pnl_usd > 0.0:
            pnl_factor = 65.0
        elif profile.total_realized_pnl_usd < -5_000.0:
            pnl_factor = 20.0
        else:
            pnl_factor = 40.0

        score = (win_rate * 0.40) + (latest_earlyness * 0.35) + (pnl_factor * 0.25)
        return round(min(max(score, 5.0), 99.0), 2)

    def evaluate_token_smart_money(self, mint: str) -> TokenSmartMoneySignal:
        """
        Combine established wallet reputation with evidence-gated cold-start intelligence.

        The emerging layer is allowed to influence the live score only when it has
        real verified quote evidence. This avoids manufacturing confidence while
        allowing strong within-run accumulation to matter before a wallet has a
        historical win/loss record.
        """
        swaps = self.token_swaps.get(mint, [])
        if not swaps:
            return TokenSmartMoneySignal(
                mint=mint,
                smart_money_score=50.0,
                netflow_usd=0.0,
                smart_buyers_count=0,
                smart_sellers_count=0,
                total_smart_volume_usd=0.0,
                signal_label="NEUTRAL",
                provenance=Provenance(
                    source_type=SourceType.REAL,
                    provider="RealSmartMoneyEngine",
                    confidence=0.5,
                ),
            )

        smart_buyers = set()
        smart_sellers = set()
        smart_buy_vol = 0.0
        smart_sell_vol = 0.0
        weighted_scores = []

        for s in swaps:
            profile = self.wallets.get(s.wallet)
            wallet_score = profile.smart_wallet_score if profile else 50.0
            weighted_scores.append(wallet_score)

            if wallet_score >= self.SMART_MONEY_THRESHOLD and is_swap_quote_verified(s):
                if s.side == "BUY":
                    smart_buyers.add(s.wallet)
                    smart_buy_vol += float(s.quote_amount_usd)
                else:
                    smart_sellers.add(s.wallet)
                    smart_sell_vol += float(s.quote_amount_usd)

        netflow = smart_buy_vol - smart_sell_vol
        avg_score = (sum(weighted_scores) / len(weighted_scores)) if weighted_scores else 50.0

        if netflow > 10_000.0:
            base_score = min(avg_score + 15.0, 98.0)
            base_label = "HEAVY_SMART_ACCUMULATION"
        elif netflow > 1_000.0:
            base_score = min(avg_score + 8.0, 95.0)
            base_label = "MODERATE_SMART_BUY"
        elif netflow < -10_000.0:
            base_score = max(avg_score - 25.0, 10.0)
            base_label = "SMART_DISTRIBUTION"
        else:
            base_score = avg_score
            base_label = "NEUTRAL"

        emerging = self.emerging_engine.evaluate_token_signal(mint)
        emerging_score = emerging.emerging_smart_score
        emerging_netflow = emerging.emerging_netflow_usd
        emerging_usable = (
            emerging_score is not None
            and emerging_quote_quality_is_usable(emerging.quote_quality)
            and emerging.signal_label != "NEUTRAL"
            and emerging_netflow is not None
        )

        final_score = base_score
        final_netflow = netflow
        final_label = base_label

        if emerging_usable:
            # Cold-start evidence can promote the score when verified accumulation
            # is materially stronger than the historical-reputation layer.
            final_score = round(min(max(base_score, float(emerging_score)), 98.0), 2)
            final_netflow = float(emerging_netflow)
            if emerging.signal_label == "HIGH_CONVICTION_ACCUMULATION" and emerging_score >= 75.0:
                final_label = "EMERGING_SMART_ACCUMULATION"
            elif emerging.signal_label == "MODERATE_ACCUMULATION" and emerging_score >= 70.0:
                final_label = "EMERGING_MODERATE_BUY"
            elif emerging.signal_label == "DISTRIBUTION" and emerging_score < 45.0:
                final_label = "EMERGING_DISTRIBUTION"

        return TokenSmartMoneySignal(
            mint=mint,
            smart_money_score=round(final_score, 2),
            netflow_usd=round(final_netflow, 2),
            smart_buyers_count=len(smart_buyers),
            smart_sellers_count=len(smart_sellers),
            total_smart_volume_usd=round(smart_buy_vol + smart_sell_vol, 2),
            signal_label=final_label,
            provenance=Provenance(
                source_type=SourceType.REAL,
                provider="RealSmartMoneyEngine",
                timestamp=time.time(),
                confidence=round(max(0.0, min(1.0, emerging.quote_quality if emerging_usable else 1.0)), 4),
                verified_on_chain=True,
            ),
            emerging_smart_money_score=round(float(emerging_score), 2) if emerging_score is not None else None,
            emerging_netflow_usd=round(float(emerging_netflow), 2) if emerging_netflow is not None else None,
            emerging_accumulating_wallets=emerging.accumulating_wallets_count,
            emerging_distributing_wallets=emerging.distributing_wallets_count,
            emerging_quote_quality=emerging.quote_quality,
            emerging_signal_label=emerging.signal_label,
        )


def emerging_smart_money_quote_quality_is_usable(quote_quality: float) -> bool:
    """Return True only when a meaningful fraction of the token's swaps is verified."""
    return quote_quality >= 0.50


# Keep the helper name close to the data layer vocabulary while remaining private.
emerging_quote_quality_is_usable = emerging_smart_money_quote_quality_is_usable
