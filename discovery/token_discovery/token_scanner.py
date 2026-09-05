"""
Token Discovery Scanner with strict Solana Base58 address validation and provenance.
"""

from dataclasses import dataclass, asdict, field
import json
import logging
import time
from typing import Any, Dict, List, Optional

from app.config.settings import DiscoveryConfig
from app.core.database import DatabaseManager
from blockchain.solana.address_validator import SolanaAddressValidator
from blockchain.solana.types import Provenance, SourceType
from data.ingestion.provider_base import BaseDataProvider

logger = logging.getLogger("meme_alpha_hunter.discovery")


@dataclass
class DiscoveredToken:
    mint: str
    symbol: str
    name: str
    decimals: int
    liquidity: float
    market_cap: float
    price: float
    volume_24h: float
    buyers_24h: int
    sellers_24h: int
    holders_count: int
    creator: str
    pool_address: str
    chain: str
    source: str
    first_seen_ts: float
    updated_at: float
    is_qualified: bool = False
    rejection_reason: Optional[str] = None
    provenance: Provenance = field(default_factory=Provenance)


class TokenDiscoveryScanner:
    def __init__(self, data_provider: BaseDataProvider, config: Optional[DiscoveryConfig] = None, db: Optional[DatabaseManager] = None):
        self.provider = data_provider
        self.config = config or DiscoveryConfig()
        self.db = db or DatabaseManager()
        self.discovered_cache: Dict[str, DiscoveredToken] = {}

    def scan(self, limit: int = 50) -> List[DiscoveredToken]:
        """Scan data provider, validate Solana mints, and register newly found tokens."""
        raw_tokens = self.provider.scan_recent_tokens(limit=limit)
        results = []

        for item in raw_tokens:
            mint = item.get("mint")
            if not mint:
                continue

            # Strict Solana Mint Address Validation
            if not SolanaAddressValidator.validate_token_mint(mint):
                logger.warning(f"REJECTED INVALID SYNTHETIC MINT: {mint}")
                continue

            market_data = self.provider.get_token_market_data(mint) or item
            token_obj = self._evaluate_and_record(market_data)
            results.append(token_obj)

        return results

    def _evaluate_and_record(self, data: Dict[str, Any]) -> DiscoveredToken:
        mint = data.get("mint", "")
        symbol = data.get("symbol", "UNKNOWN")
        name = data.get("name", "Unknown")
        decimals = int(data.get("decimals", 9))
        liquidity = float(data.get("liquidity", 0.0))
        market_cap = float(data.get("market_cap", 0.0))
        price = float(data.get("price", 0.0))
        volume_24h = float(data.get("volume_24h", 0.0))
        buyers_24h = int(data.get("buyers_24h", 0))
        sellers_24h = int(data.get("sellers_24h", 0))
        holders_count = int(data.get("holders_count", 0))
        creator = data.get("creator", "")
        pool_address = data.get("pool_address", "")
        chain = data.get("chain", "solana")
        source = data.get("source", "DexScanner")
        first_seen_ts = float(data.get("first_seen_ts", time.time()))
        updated_at = time.time()

        # Provenance handling
        prov_dict = data.get("provenance", {})
        if isinstance(prov_dict, dict) and prov_dict:
            src_type_str = prov_dict.get("source_type", "REAL")
            src_type = SourceType(src_type_str) if src_type_str in SourceType._value2member_map_ else SourceType.REAL
            provenance = Provenance(
                source_type=src_type,
                provider=prov_dict.get("provider", source),
                timestamp=float(prov_dict.get("timestamp", time.time())),
                observed_at=float(prov_dict.get("observed_at", time.time())),
                confidence=float(prov_dict.get("confidence", 1.0)),
                verified_on_chain=bool(prov_dict.get("verified_on_chain", False))
            )
        else:
            provenance = self.provider.create_provenance(confidence=0.9, verified_on_chain=True)

        # Filtering logic
        is_qualified = True
        rejection_reason = None

        if liquidity < self.config.min_liquidity_usd:
            is_qualified = False
            rejection_reason = f"Liquidity ${liquidity:,.0f} < ${self.config.min_liquidity_usd:,.0f} min"
        elif volume_24h < self.config.min_volume_24h_usd:
            is_qualified = False
            rejection_reason = f"Volume 24h ${volume_24h:,.0f} < ${self.config.min_volume_24h_usd:,.0f} min"
        elif market_cap < self.config.min_market_cap_usd:
            is_qualified = False
            rejection_reason = f"Market Cap ${market_cap:,.0f} < ${self.config.min_market_cap_usd:,.0f} min"
        elif holders_count < self.config.min_holders_count:
            is_qualified = False
            rejection_reason = f"Holders {holders_count} < {self.config.min_holders_count} min"

        token_obj = DiscoveredToken(
            mint=mint,
            symbol=symbol,
            name=name,
            decimals=decimals,
            liquidity=liquidity,
            market_cap=market_cap,
            price=price,
            volume_24h=volume_24h,
            buyers_24h=buyers_24h,
            sellers_24h=sellers_24h,
            holders_count=holders_count,
            creator=creator,
            pool_address=pool_address,
            chain=chain,
            source=source,
            first_seen_ts=first_seen_ts,
            updated_at=updated_at,
            is_qualified=is_qualified,
            rejection_reason=rejection_reason,
            provenance=provenance
        )

        self.discovered_cache[mint] = token_obj

        # Persist to database
        try:
            db_dict = asdict(token_obj)
            db_dict["provenance"] = json.dumps(provenance.to_dict())
            self.db.upsert_token(db_dict)
        except Exception as e:
            logger.error(f"Failed to persist token {mint}: {e}")

        return token_obj
