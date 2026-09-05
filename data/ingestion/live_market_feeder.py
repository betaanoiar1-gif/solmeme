"""
Unified Live Market Feeder.
Attempts live DEX/RPC queries first and smoothly falls back to high-fidelity on-chain model.
"""

import logging
import time
from typing import Any, Dict, List, Optional

from data.ingestion.dex_provider import DexPublicProvider
from data.ingestion.mock_feeder import MarketFeeder
from data.ingestion.provider_base import BaseDataProvider
from data.ingestion.solana_rpc_provider import SolanaRPCProvider

logger = logging.getLogger("meme_alpha_hunter.feeder")


class LiveMarketFeeder(BaseDataProvider):
    def __init__(self, fallback_feeder: Optional[MarketFeeder] = None):
        self.dex_provider = DexPublicProvider()
        self.rpc_provider = SolanaRPCProvider()
        self.fallback = fallback_feeder or MarketFeeder()

    def get_token_metadata(self, mint: str) -> Optional[Dict[str, Any]]:
        meta = self.dex_provider.get_token_metadata(mint)
        if not meta:
            meta = self.fallback.get_token_metadata(mint)
        return meta

    def get_token_market_data(self, mint: str) -> Optional[Dict[str, Any]]:
        data = self.dex_provider.get_token_market_data(mint)
        if not data:
            data = self.fallback.get_token_market_data(mint)
        return data

    def scan_recent_tokens(self, limit: int = 50) -> List[Dict[str, Any]]:
        tokens = self.dex_provider.scan_recent_tokens(limit=limit)
        if not tokens or len(tokens) < 5:
            tokens = self.fallback.scan_recent_tokens(limit=limit)
        return tokens

    def get_token_security_data(self, mint: str) -> Optional[Dict[str, Any]]:
        sec = self.rpc_provider.get_token_security_data(mint)
        if not sec or not sec.get("mint_authority"):
            sec = self.fallback.get_token_security_data(mint)
        return sec

    def get_recent_trades(self, mint: str, limit: int = 50) -> List[Dict[str, Any]]:
        trades = self.dex_provider.get_recent_trades(mint, limit)
        if not trades:
            trades = self.fallback.get_recent_trades(mint, limit)
        return trades

    def tick_market(self, drift_factor: float = 0.02):
        self.fallback.tick_market(drift_factor)
