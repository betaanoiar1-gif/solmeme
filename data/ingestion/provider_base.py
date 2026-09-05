"""
Base abstract data provider interface.
Ensures zero hard-coupling to any single commercial API.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseDataProvider(ABC):
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
