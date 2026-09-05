"""
Solana Liquidity Pool Scanner.
Monitors Raydium CPMM / AMM, Pump.fun bonding curves, and Meteora DLMM pools.
"""

from typing import Any, Dict, List, Optional
from blockchain.solana.types import LiquidityPool


class PoolDiscoveryScanner:
    def __init__(self):
        self.known_pools: Dict[str, LiquidityPool] = {}

    def register_pool(self, pool: LiquidityPool) -> LiquidityPool:
        self.known_pools[pool.pool_address] = pool
        return pool

    def get_pool_by_mint(self, token_mint: str) -> Optional[LiquidityPool]:
        for pool in self.known_pools.values():
            if pool.token_mint == token_mint:
                return pool
        return None

    def get_all_pools(self) -> List[LiquidityPool]:
        return list(self.known_pools.values())
