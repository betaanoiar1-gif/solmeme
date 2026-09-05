"""
Solana data models, cryptographic types, and strict provenance models.
"""

from dataclasses import dataclass, field
from enum import Enum
import time
from typing import Any, Dict, List, Optional


class SourceType(str, Enum):
    REAL = "REAL"
    MOCK = "MOCK"
    REPLAY = "REPLAY"


@dataclass
class Provenance:
    source_type: SourceType = SourceType.REAL
    provider: str = "solana_rpc"
    timestamp: float = field(default_factory=time.time)
    observed_at: float = field(default_factory=time.time)
    block_time: Optional[float] = None
    confidence: float = 1.0
    verified_on_chain: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_type": self.source_type.value if isinstance(self.source_type, SourceType) else str(self.source_type),
            "provider": self.provider,
            "timestamp": self.timestamp,
            "observed_at": self.observed_at,
            "block_time": self.block_time,
            "confidence": self.confidence,
            "verified_on_chain": self.verified_on_chain
        }


@dataclass
class TokenMetadata:
    mint: str
    symbol: str
    name: str
    decimals: int = 9
    creator: str = ""
    description: str = ""
    image_uri: str = ""
    supply: float = 1_000_000_000.0
    provenance: Provenance = field(default_factory=Provenance)


@dataclass
class LiquidityPool:
    pool_address: str
    token_mint: str
    quote_mint: str = "So11111111111111111111111111111111111111112"  # WSOL
    dex_type: str = "Raydium"  # Raydium, PumpFun, Meteora, Orca
    base_reserve: float = 0.0
    quote_reserve: float = 0.0
    liquidity_usd: float = 0.0
    price_usd: float = 0.0
    is_locked: bool = False
    lock_percent: float = 0.0
    created_at: float = field(default_factory=time.time)
    provenance: Provenance = field(default_factory=Provenance)


@dataclass
class OnChainTransaction:
    signature: str
    slot: int
    timestamp: float
    signer: str
    token_mint: str
    pool_address: str
    type: str  # "BUY", "SELL", "CREATE_POOL", "ADD_LIQUIDITY", "REMOVE_LIQUIDITY"
    token_amount: float
    sol_amount: float
    usd_amount: float
    price_usd: float
    fee_sol: float = 0.000005
    provenance: Provenance = field(default_factory=Provenance)
