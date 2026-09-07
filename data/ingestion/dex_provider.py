"""
Public DEX Data Provider (DexScreener, Jupiter, Raydium APIs) with health metrics.
"""

import copy
import json
import logging
import time
from typing import Any, Dict, List, Optional
import urllib.request

from blockchain.solana.types import SourceType
from data.ingestion.provider_base import BaseDataProvider

logger = logging.getLogger("meme_alpha_hunter.dex_provider")


class DexPublicProvider(BaseDataProvider):
    """
    Live DEX reader designed around market-state freshness rather than request volume.
    Short-lived caches reduce duplicate reads inside rapid scan cycles while preserving
    the original source timestamp/provenance of cached observations.
    """

    def __init__(self, timeout: float = 3.0, max_retries: int = 1):
        super().__init__(source_type=SourceType.REAL, provider_name="DexScreenerPublic")
        self.timeout = timeout
        self.max_retries = max_retries
        self.headers = {"User-Agent": "MemeAlphaHunter/1.0"}
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.last_error_time = 0.0
        self._market_cache: Dict[str, Dict[str, Any]] = {}
        self._market_cache_ttl_sec = 5.0
        self._discovery_cache: Optional[Dict[str, Any]] = None
        self._discovery_cache_ttl_sec = 3.0

    def _get_json(self, url: str) -> Optional[Any]:
        self.total_requests += 1
        for attempt in range(self.max_retries):
            try:
                req = urllib.request.Request(url, headers=self.headers)
                with urllib.request.urlopen(req, timeout=self.timeout) as response:
                    data = json.loads(response.read().decode("utf-8"))
                    self.successful_requests += 1
                    return data
            except Exception as e:
                self.failed_requests += 1
                self.last_error_time = time.time()
                logger.debug(f"HTTP fetch attempt {attempt + 1} failed for {url}: {e}")
                if attempt + 1 < self.max_retries:
                    time.sleep(0.1 * (2 ** attempt))
        return None

    def get_token_metadata(self, mint: str) -> Optional[Dict[str, Any]]:
        data = self.get_token_market_data(mint)
        if data:
            return {
                "mint": mint,
                "symbol": data.get("symbol", "UNKNOWN"),
                "name": data.get("name", "Unknown Token"),
                "decimals": 9,
                "creator": data.get("creator", ""),
                "provenance": data.get("provenance", self.create_provenance(confidence=0.9).to_dict()),
            }
        return None

    @staticmethod
    def _select_solana_pair(pairs: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        solana_pairs = [p for p in pairs if p.get("chainId") == "solana"]
        candidates = solana_pairs or pairs
        if not candidates:
            return None
        # Liquidity is the execution-quality criterion; pair creation time is the
        # next tie-breaker so the scanner does not blindly choose the first pair.
        return max(
            candidates,
            key=lambda p: (
                float(((p.get("liquidity") or {}).get("usd")) or 0.0),
                float(p.get("pairCreatedAt") or 0.0),
            ),
        )

    def get_token_market_data(self, mint: str) -> Optional[Dict[str, Any]]:
        now = time.time()
        cached = self._market_cache.get(mint)
        if cached and now - cached["cached_at"] < self._market_cache_ttl_sec:
            return copy.deepcopy(cached["data"])

        url = f"https://api.dexscreener.com/latest/dex/tokens/{mint}"
        res = self._get_json(url)
        if not isinstance(res, dict) or not res.get("pairs"):
            return None

        pair = self._select_solana_pair(res["pairs"])
        if pair is None:
            return None

        pair_created = float(pair["pairCreatedAt"]) / 1000.0 if pair.get("pairCreatedAt") is not None else None
        price_val = float(pair["priceUsd"]) if pair.get("priceUsd") is not None else None
        liq_val = float(pair["liquidity"]["usd"]) if (pair.get("liquidity") and pair["liquidity"].get("usd") is not None) else None
        mcap_val = float(pair["fdv"]) if pair.get("fdv") is not None else None
        vol_val = float(pair["volume"]["h24"]) if (pair.get("volume") and pair["volume"].get("h24") is not None) else None
        vol_5m = float(pair["volume"]["m5"]) if (pair.get("volume") and pair["volume"].get("m5") is not None) else None
        vol_1h = float(pair["volume"]["h1"]) if (pair.get("volume") and pair["volume"].get("h1") is not None) else None
        buys_24h = int(pair["txns"]["h24"]["buys"]) if (pair.get("txns") and pair["txns"].get("h24") and pair["txns"]["h24"].get("buys") is not None) else 0
        sells_24h = int(pair["txns"]["h24"]["sells"]) if (pair.get("txns") and pair["txns"].get("h24") and pair["txns"]["h24"].get("sells") is not None) else 0

        data = {
            "mint": mint,
            "symbol": pair.get("baseToken", {}).get("symbol", ""),
            "name": pair.get("baseToken", {}).get("name", ""),
            "price": price_val,
            "liquidity": liq_val,
            "market_cap": mcap_val,
            "volume_24h": vol_val,
            "volume_5m": vol_5m,
            "volume_1h": vol_1h,
            "buyers_24h": buys_24h,
            "sellers_24h": sells_24h,
            "pool_address": pair.get("pairAddress", ""),
            "dex": pair.get("dexId", "raydium"),
            "pair_created_at": pair_created,
            "chain": pair.get("chainId", "solana"),
            "source": "DexScreener",
            "first_seen_ts": pair_created,
            "updated_at": now,
            "provenance": self.create_provenance(confidence=0.95, verified_on_chain=False).to_dict(),
        }
        self._market_cache[mint] = {"cached_at": now, "data": copy.deepcopy(data)}
        return data

    def scan_recent_tokens(self, limit: int = 50) -> List[Dict[str, Any]]:
        now = time.time()
        if self._discovery_cache and now - self._discovery_cache["cached_at"] < self._discovery_cache_ttl_sec:
            return copy.deepcopy(self._discovery_cache["tokens"][:limit])

        url = "https://api.dexscreener.com/token-profiles/latest/v1"
        res = self._get_json(url)
        tokens: List[Dict[str, Any]] = []

        if isinstance(res, list):
            for item in res:
                if item.get("chainId") != "solana":
                    continue
                mint = item.get("tokenAddress")
                if not mint:
                    continue
                market = self.get_token_market_data(mint)
                if market is None:
                    logger.debug("Skipping discovered token %s: no live market pair", mint)
                    continue
                market["source"] = "DexScreenerProfiles+Market"
                market["discovery_description"] = (item.get("description") or "")[:200]
                market["discovery_url"] = item.get("url")
                tokens.append(market)
                if len(tokens) >= limit:
                    break

        tokens.sort(key=lambda x: (x.get("first_seen_ts") or 0.0, x.get("liquidity") or 0.0), reverse=True)
        self._discovery_cache = {"cached_at": now, "tokens": copy.deepcopy(tokens)}
        return tokens

    def get_token_security_data(self, mint: str) -> Optional[Dict[str, Any]]:
        return None

    def get_recent_trades(self, mint: str, limit: int = 50) -> List[Dict[str, Any]]:
        return []
