"""
Real Whale Activity Tracker for Solana.
Operates strictly on real observed on-chain transactions and swaps.
Tracks BUY, SELL, ACCUMULATION, and DISTRIBUTION events.
"""

from dataclasses import dataclass, field
import logging
import time
from typing import Any, Dict, List, Optional

from app.core.database import DatabaseManager
from blockchain.parsers.real_swap_parser import RealSwapRecord
from blockchain.solana.types import Provenance, SourceType

logger = logging.getLogger("meme_alpha_hunter.whale_tracker")


@dataclass
class RealWhaleEvent:
    event_id: str
    wallet: str
    token_mint: str
    action: str  # "BUY", "SELL", "ACCUMULATION", "DISTRIBUTION"
    amount_tokens: float
    usd_estimate: float
    timestamp: float
    signature: str
    pool: str
    source: str
    impact_score: float  # 0 to 100
    provenance: Provenance = field(default_factory=Provenance)


class RealWhaleTracker:
    WHALE_THRESHOLD_USD = 5000.0  # Min single trade size to qualify as whale
    ACCUMULATION_THRESHOLD_USD = 15000.0  # Cumulative buy volume to qualify as accumulation

    def __init__(self, db: Optional[DatabaseManager] = None):
        self.db = db or DatabaseManager()
        self.events: List[RealWhaleEvent] = []
        self._wallet_positions: Dict[str, Dict[str, float]] = {}  # wallet -> {mint -> net_usd_invested}
        self._token_whale_flows: Dict[str, float] = {}  # mint -> netflow_usd

    def process_real_swap(self, swap: RealSwapRecord, pool_liquidity_usd: Optional[float] = None) -> Optional[RealWhaleEvent]:
        """
        Evaluates a real swap for whale impact.
        Classifies single large trades as BUY / SELL,
        and sustained buying / liquidating as ACCUMULATION / DISTRIBUTION.
        Zero hardcoded default pool liquidity ($50,000).
        """
        usd_val = swap.quote_amount_usd
        if usd_val is None or not swap.is_quote_verified:
            # Cannot determine USD size reliably; do not process as whale
            return None

        is_whale_size = (usd_val >= self.WHALE_THRESHOLD_USD) or (
            pool_liquidity_usd is not None and pool_liquidity_usd > 0 and (usd_val / pool_liquidity_usd >= 0.015)
        )

        wallet = swap.wallet
        mint = swap.mint

        if wallet not in self._wallet_positions:
            self._wallet_positions[wallet] = {}
        prev_net = self._wallet_positions[wallet].get(mint, 0.0)

        if swap.side == "BUY":
            new_net = prev_net + usd_val
            flow_delta = usd_val
        else:
            new_net = max(prev_net - usd_val, 0.0)
            flow_delta = -usd_val

        self._wallet_positions[wallet][mint] = new_net
        self._token_whale_flows[mint] = self._token_whale_flows.get(mint, 0.0) + flow_delta

        if not is_whale_size and abs(flow_delta) < self.WHALE_THRESHOLD_USD:
            return None

        # Classify Action
        if swap.side == "BUY":
            if new_net >= self.ACCUMULATION_THRESHOLD_USD:
                action = "ACCUMULATION"
            else:
                action = "BUY"
        else:
            if prev_net >= self.ACCUMULATION_THRESHOLD_USD and new_net < 1000.0:
                action = "DISTRIBUTION"
            else:
                action = "SELL"

        # Impact score based on % of pool liquidity (neutral 50.0 if unknown)
        if pool_liquidity_usd is not None and pool_liquidity_usd > 0:
            impact_pct = (usd_val / pool_liquidity_usd) * 100.0
            impact_score = min(max(impact_pct * 10.0, 10.0), 100.0)
        else:
            impact_score = 50.0

        event_id = f"whale_{swap.signature[:8]}_{int(swap.timestamp)}"

        event = RealWhaleEvent(
            event_id=event_id,
            wallet=wallet,
            token_mint=mint,
            action=action,
            amount_tokens=swap.token_amount,
            usd_estimate=round(usd_val, 2),
            timestamp=swap.timestamp,
            signature=swap.signature,
            pool=swap.pool,
            source=swap.venue,
            impact_score=round(impact_score, 2),
            provenance=swap.provenance
        )

        self.events.append(event)

        # Persist to DB
        try:
            self.db.record_whale_event({
                "event_id": event.event_id,
                "wallet": event.wallet,
                "mint": event.token_mint,
                "action": event.action,
                "amount_usd": event.usd_estimate,
                "token_amount": event.amount_tokens,
                "price": swap.price_usd,
                "impact_score": event.impact_score,
                "timestamp": event.timestamp
            })
        except Exception as e:
            logger.error(f"Failed to persist whale event: {e}")

        return event

    def get_token_whale_netflow(self, mint: str) -> float:
        """Returns live calculated netflow from real whale swaps."""
        return self._token_whale_flows.get(mint, 0.0)

    def get_recent_whale_events(self, mint: Optional[str] = None, limit: int = 50) -> List[RealWhaleEvent]:
        if mint:
            return [e for e in self.events if e.token_mint == mint][-limit:]
        return self.events[-limit:]
