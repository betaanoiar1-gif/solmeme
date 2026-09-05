"""
Solana data models and cryptographic types.
"""

from dataclasses import dataclass, field
import time
from typing import Any, Dict, List, Optional


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
