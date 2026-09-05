"""
Base abstract data provider interface with strict provenance.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from blockchain.solana.types import Provenance, SourceType


class BaseDataProvider(ABC):
    def __init__(self, source_type: SourceType = SourceType.REAL, provider_name: str = "generic_provider"):
        self.source_type = source_type
        self.provider_name = provider_name

    def create_provenance(self, confidence: float = 1.0, verified_on_chain: bool = False, block_time: Optional[float] = None) -> Provenance:
        return Provenance(
            source_type=self.source_type,
            provider=self.provider_name,
            confidence=confidence,
            verified_on_chain=verified_on_chain,
            block_time=block_time
        )

    @abstractmethod
    def get_token_metadata(self, mint: str) -> Optional[Dict[str, Any]]:
        """Fetch token metadata (symbol, name, supply, decimals, creator)."""
        pass

    @abstractmethod
    def get_token_market_data(self, mint: str) -> Optional[Dict[str, Any]]:
        """Fetch real-time price, volume, liquidity, market cap, buyer/seller counts."""
        pass

    @abstractmethod
    def scan_recent_tokens(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Scan recent tokens, pools, and bonding curves."""
        pass

    @abstractmethod
    def get_token_security_data(self, mint: str) -> Optional[Dict[str, Any]]:
        """Fetch mint authority, freeze authority, top holders, and LP lock percentage."""
        pass

    @abstractmethod
    def get_recent_trades(self, mint: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Fetch recent trade flow / transactions for microstructure and whale tracking."""
        pass
