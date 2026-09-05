"""
Token DNA Engine.
Maintains continuous time-series history for price, volume, liquidity,
holders, smart money flow, and phase progression.
"""

from dataclasses import dataclass, field
import time
from typing import Any, Dict, List, Optional
from app.core.database import DatabaseManager


@dataclass
class DNASnapshot:
    timestamp: float
    price: Optional[float]
    volume: Optional[float]
    liquidity: Optional[float]
    holders: Optional[int]
    smart_money_flow: float = 0.0
    whale_netflow: float = 0.0
    regime: str = "R2_ACCUMULATION"


class TokenDNAEngine:
    def __init__(self, db: Optional[DatabaseManager] = None):
        self.db = db or DatabaseManager()
        self._cache: Dict[str, List[DNASnapshot]] = {}

    def record_snapshot(
        self,
        mint: str,
        price: Optional[float],
        volume: Optional[float] = None,
        liquidity: Optional[float] = None,
        holders: Optional[int] = None,
        smart_money_flow: float = 0.0,
        whale_netflow: float = 0.0,
        regime: str = "R2_ACCUMULATION",
        ts: Optional[float] = None
    ) -> DNASnapshot:
        timestamp = ts or time.time()
        snap = DNASnapshot(
            timestamp=timestamp,
            price=price,
            volume=volume,
            liquidity=liquidity,
            holders=holders,
            smart_money_flow=smart_money_flow,
            whale_netflow=whale_netflow,
            regime=regime
        )

        if mint not in self._cache:
            self._cache[mint] = []
        self._cache[mint].append(snap)

        try:
            self.db.record_dna_snapshot({
                "mint": mint,
                "timestamp": timestamp,
                "price": price,
                "volume": volume,
                "liquidity": liquidity,
                "holders": holders,
                "smart_money_flow": smart_money_flow,
                "whale_netflow": whale_netflow,
                "regime": regime
            })
        except Exception:
            pass

        return snap

    def get_history(self, mint: str) -> List[DNASnapshot]:
        if mint in self._cache:
            return self._cache[mint]
        db_rows = self.db.get_token_dna(mint)
        snaps = [
            DNASnapshot(
                timestamp=r["timestamp"],
                price=r["price"],
                volume=r["volume"],
                liquidity=r["liquidity"],
                holders=r["holders"],
                smart_money_flow=r["smart_money_flow"],
                whale_netflow=r["whale_netflow"],
                regime=r["regime"]
            )
            for r in db_rows
        ]
        self._cache[mint] = snaps
        return snaps
