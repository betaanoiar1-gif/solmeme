"""
Solana RPC Provider implementation.
"""

from typing import Any, Dict, List, Optional
from blockchain.rpc.rpc_client import SolanaRPCClient
from data.ingestion.provider_base import BaseDataProvider


class SolanaRPCProvider(BaseDataProvider):
    def __init__(self, rpc_client: Optional[SolanaRPCClient] = None):
        self.rpc = rpc_client or SolanaRPCClient()

    def get_token_metadata(self, mint: str) -> Optional[Dict[str, Any]]:
        acc = self.rpc.get_account_info(mint)
        if acc:
            return {
                "mint": mint,
                "symbol": "SOL-TOKEN",
                "name": "Solana Token",
                "decimals": 9,
                "creator": "unknown_creator"
            }
        return None

    def get_token_market_data(self, mint: str) -> Optional[Dict[str, Any]]:
        return None

    def scan_recent_tokens(self, limit: int = 50) -> List[Dict[str, Any]]:
        return []

    def get_token_security_data(self, mint: str) -> Optional[Dict[str, Any]]:
        acc = self.rpc.get_account_info(mint)
        if acc:
            data = acc.get("data", {})
            parsed = data.get("parsed", {}).get("info", {})
            return {
                "mint": mint,
                "mint_authority": parsed.get("mintAuthority"),
                "freeze_authority": parsed.get("freezeAuthority"),
                "is_initialized": parsed.get("isInitialized", True),
                "decimals": parsed.get("decimals", 9)
            }
        return None

    def get_recent_trades(self, mint: str, limit: int = 50) -> List[Dict[str, Any]]:
        return []
