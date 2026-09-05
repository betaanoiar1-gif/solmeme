"""
Strict Live Market Feeder with zero silent mock contamination.
In 'live' mode, only real Solana endpoints are queried.
If live network is unreachable, it explicitly reports UNAVAILABLE without mock fallback.
"""

import logging
import os
import time
from typing import Any, Dict, List, Optional

from blockchain.solana.types import Provenance, SourceType
from data.ingestion.dex_provider import DexPublicProvider
from data.ingestion.mock_feeder import MarketFeeder
from data.ingestion.provider_base import BaseDataProvider
from data.ingestion.solana_rpc_provider import SolanaRPCProvider

logger = logging.getLogger("meme_alpha_hunter.feeder")


class LiveMarketFeeder(BaseDataProvider):
    def __init__(self, data_mode: str = "live", mock_feeder: Optional[MarketFeeder] = None):
        self.data_mode = os.getenv("DATA_MODE", data_mode).lower()
        super().__init__(
            source_type=SourceType.REAL if self.data_mode == "live" else SourceType.MOCK,
            provider_name="SolanaLiveMainnet" if self.data_mode == "live" else "MarketFeederMock"
        )
        self.dex_provider = DexPublicProvider()
        self.rpc_provider = SolanaRPCProvider()
        self.mock_feeder = mock_feeder or (MarketFeeder() if self.data_mode in ("mock", "replay") else None)
        self.live_data_available = False
        self.last_live_probe_time = 0.0

    def probe_live_network(self) -> bool:
        """Test live connectivity to DEX and RPC endpoints."""
        if self.data_mode != "live":
            return False
        # Try a fast probe
        meta = self.dex_provider.get_token_market_data("So11111111111111111111111111111111111111112")
        self.live_data_available = bool(meta)
        self.last_live_probe_time = time.time()
        return self.live_data_available

    def get_token_metadata(self, mint: str) -> Optional[Dict[str, Any]]:
        if self.data_mode == "live":
            meta = self.dex_provider.get_token_metadata(mint) or self.rpc_provider.get_token_metadata(mint)
            return meta
        elif self.mock_feeder:
            return self.mock_feeder.get_token_metadata(mint)
        return None

    def get_token_market_data(self, mint: str) -> Optional[Dict[str, Any]]:
        if self.data_mode == "live":
            data = self.dex_provider.get_token_market_data(mint)
            return data
        elif self.mock_feeder:
            return self.mock_feeder.get_token_market_data(mint)
        return None

    def scan_recent_tokens(self, limit: int = 50) -> List[Dict[str, Any]]:
        if self.data_mode == "live":
            tokens = self.dex_provider.scan_recent_tokens(limit=limit)
            if not tokens:
                logger.info("LIVE DATA UNAVAILABLE: No real tokens returned from live DEX endpoints.")
            return tokens
        elif self.mock_feeder:
            return self.mock_feeder.scan_recent_tokens(limit=limit)
        return []

    def get_token_security_data(self, mint: str) -> Optional[Dict[str, Any]]:
        if self.data_mode == "live":
            sec = self.rpc_provider.get_token_security_data(mint)
            return sec
        elif self.mock_feeder:
            return self.mock_feeder.get_token_security_data(mint)
        return None

    def get_recent_trades(self, mint: str, limit: int = 50) -> List[Dict[str, Any]]:
        if self.data_mode == "live":
            trades = self.dex_provider.get_recent_trades(mint, limit)
            return trades
        elif self.mock_feeder:
            return self.mock_feeder.get_recent_trades(mint, limit)
        return []

    def tick_market(self, drift_factor: float = 0.02):
        if self.mock_feeder and self.data_mode in ("mock", "replay"):
            self.mock_feeder.tick_market(drift_factor)
