"""
Whale Radar.
Tracks high-capital Solana wallets, detects accumulation/distribution patterns,
and calculates net whale flow impact.
"""

from dataclasses import dataclass
import logging
import time
from typing import Any, Dict, List, Optional
import uuid

from app.core.database import DatabaseManager

logger = logging.getLogger("meme_alpha_hunter.whale_radar")


@dataclass
class WhaleSignal:
    event_id: str
    wallet: str
    mint: str
    action: str  # "WHALE_BUY", "WHALE_SELL", "WHALE_ACCUMULATION", "WHALE_DISTRIBUTION"
    amount_usd: float
    token_amount: float
    price: float
    impact_score: float  # 0 to 100
    timestamp: float


class WhaleRadar:
    WHALE_THRESHOLD_USD = 2_500.0  # Minimum trade size to trigger whale radar

    def __init__(self, db: Optional[DatabaseManager] = None):
        self.db = db or DatabaseManager()
        self._wallet_histories: Dict[str, List[Dict[str, Any]]] = {}

    def process_trade(self, trade: Dict[str, Any], token_liquidity: float) -> Optional[WhaleSignal]:
        usd_amount = float(trade.get("usd_amount", 0.0))
        if usd_amount < self.WHALE_THRESHOLD_USD:
            return None

        wallet = trade.get("signer", "UnknownWhale")
        mint = trade.get("token_mint", "")
        tx_type = trade.get("type", "BUY")
        price = float(trade.get("price_usd", 0.0))
        token_amt = float(trade.get("token_amount", 0.0))
        ts = float(trade.get("timestamp", time.time()))

        # Calculate price impact on pool
        impact_pct = (usd_amount / max(token_liquidity, 1_000.0)) * 100.0
        impact_score = min(max(impact_pct * 10.0, 10.0), 100.0)

        # Track history for accumulation / distribution detection
        key = f"{wallet}:{mint}"
        if key not in self._wallet_histories:
            self._wallet_histories[key] = []
        self._wallet_histories[key].append({"type": tx_type, "usd": usd_amount, "ts": ts})

        history = self._wallet_histories[key]
        recent_buys = sum(1 for t in history[-5:] if t["type"] == "BUY")
        recent_sells = sum(1 for t in history[-5:] if t["type"] == "SELL")

        if recent_buys >= 3:
            action = "WHALE_ACCUMULATION"
        elif recent_sells >= 3:
            action = "WHALE_DISTRIBUTION"
        elif tx_type == "BUY":
            action = "WHALE_BUY"
        else:
            action = "WHALE_SELL"

        signal = WhaleSignal(
            event_id=str(uuid.uuid4())[:8],
            wallet=wallet,
            mint=mint,
            action=action,
            amount_usd=usd_amount,
            token_amount=token_amt,
            price=price,
            impact_score=round(impact_score, 2),
            timestamp=ts
        )

        try:
            self.db.record_whale_event({
                "event_id": signal.event_id,
                "wallet": signal.wallet,
                "mint": signal.mint,
                "action": signal.action,
                "amount_usd": signal.amount_usd,
                "token_amount": signal.token_amount,
                "price": signal.price,
                "impact_score": signal.impact_score,
                "timestamp": signal.timestamp
            })
        except Exception:
            pass

        return signal

    def get_token_whale_netflow(self, mint: str) -> float:
        events = self.db.get_whale_events(limit=100)
        netflow = 0.0
        for ev in events:
            if ev["mint"] == mint:
                if "BUY" in ev["action"] or "ACCUMULATION" in ev["action"]:
                    netflow += ev["amount_usd"]
                else:
                    netflow -= ev["amount_usd"]
        return netflow
