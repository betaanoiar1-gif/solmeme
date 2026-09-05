"""
Solana public endpoints and fallback rotation pool.
"""

from typing import List

DEFAULT_PUBLIC_RPC_ENDPOINTS: List[str] = [
    "https://api.mainnet-beta.solana.com",
    "https://solana-mainnet.rpc.extrnode.com",
    "https://rpc.ankr.com/solana",
    "https://solana.public-rpc.com",
    "https://mainnet.helius-rpc.com/?api-key=free"
]

DEFAULT_DEX_API_ENDPOINTS: List[str] = [
    "https://api.dexscreener.com/latest/dex",
    "https://price.jup.ag/v6",
    "https://api-v3.raydium.io"
]
