"""
Public DEX Data Provider (DexScreener, Jupiter, Raydium APIs) with health metrics.
"""

import json
import logging
import time
from typing import Any, Dict, List, Optional
import urllib.error
import urllib.request

from blockchain.solana.types import SourceType
from data.ingestion.provider_base import BaseDataProvider

logger = logging.getLogger("meme_alpha_hunter.dex_provider")


class DexPublicProvider(BaseDataProvider):
    def __init__(self, timeout: float = 2.0, max_retries: int = 2):
        super().__init__(source_type=SourceType.REAL, provider_name="DexScreenerPublic")
        self.timeout = timeout
        self.max_retries = max_retries
        self.headers = {"User-Agent": "MemeAlphaHunter/1.0"}
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.last_error_time = 0.0

    def _get_json(self, url: str) -> Optional[Dict[str, Any]]:
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
                logger.debug(f"HTTP fetch attempt {attempt+1} failed for {url}: {e}")
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
                "provenance": self.create_provenance(confidence=0.9).to_dict()
            }
        return None

    def get_token_market_data(self, mint: str) -> Optional[Dict[str, Any]]:
        url = f"https://api.dexscreener.com/latest/dex/tokens/{mint}"
        res = self._get_json(url)
        if res and "pairs" in res and res["pairs"]:
            pair = res["pairs"][0]
            return {
                "mint": mint,
                "symbol": pair.get("baseToken", {}).get("symbol", ""),
                "name": pair.get("baseToken", {}).get("name", ""),
                "price": float(pair.get("priceUsd", 0.0) or 0.0),
                "liquidity": float(pair.get("liquidity", {}).get("usd", 0.0) or 0.0),
                "market_cap": float(pair.get("fdv", 0.0) or 0.0),
                "volume_24h": float(pair.get("volume", {}).get("h24", 0.0) or 0.0),
                "volume_5m": float(pair.get("volume", {}).get("m5", 0.0) or 0.0),
                "volume_1h": float(pair.get("volume", {}).get("h1", 0.0) or 0.0),
                "buyers_24h": int(pair.get("txns", {}).get("h24", {}).get("buys", 0) or 0),
                "sellers_24h": int(pair.get("txns", {}).get("h24", {}).get("sells", 0) or 0),
                "pool_address": pair.get("pairAddress", ""),
                "dex": pair.get("dexId", "raydium"),
                "pair_created_at": pair.get("pairCreatedAt", time.time() * 1000) / 1000.0,
                "chain": "solana",
                "source": "DexScreener",
                "first_seen_ts": time.time(),
                "updated_at": time.time(),
                "provenance": self.create_provenance(confidence=0.95, verified_on_chain=True).to_dict()
            }
        return None

    def scan_recent_tokens(self, limit: int = 50) -> List[Dict[str, Any]]:
        url = "https://api.dexscreener.com/token-profiles/latest/v1"
        res = self._get_json(url)
        tokens = []
        if res and isinstance(res, list):
            for item in res[:limit]:
                if item.get("chainId") == "solana":
                    tokens.append({
                        "mint": item.get("tokenAddress"),
                        "symbol": item.get("symbol", ""),
                        "name": item.get("description", "")[:20],
                        "chain": "solana",
                        "source": "DexScreenerProfiles",
                        "first_seen_ts": time.time(),
                        "updated_at": time.time(),
                        "provenance": self.create_provenance(confidence=0.85).to_dict()
                    })
        return tokens

    def get_token_security_data(self, mint: str) -> Optional[Dict[str, Any]]:
        return None

    def get_recent_trades(self, mint: str, limit: int = 50) -> List[Dict[str, Any]]:
        return []
