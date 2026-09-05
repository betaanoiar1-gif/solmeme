"""
Public DEX Data Provider (DexScreener, Jupiter, Raydium APIs).
"""

import json
import logging
import time
from typing import Any, Dict, List, Optional
import urllib.error
import urllib.request

from data.ingestion.provider_base import BaseDataProvider

logger = logging.getLogger("meme_alpha_hunter.dex_provider")


class DexPublicProvider(BaseDataProvider):
    def __init__(self, timeout: float = 0.5):
        self.timeout = timeout
        self.headers = {"User-Agent": "MemeAlphaHunter/1.0"}
        self._network_available = True

    def _get_json(self, url: str) -> Optional[Dict[str, Any]]:
        if not self._network_available:
            return None
        try:
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as e:
            logger.debug(f"HTTP fetch failed for {url}: {e}")
            self._network_available = False
            return None

    def get_token_metadata(self, mint: str) -> Optional[Dict[str, Any]]:
        data = self.get_token_market_data(mint)
        if data:
            return {
                "mint": mint,
                "symbol": data.get("symbol", "UNKNOWN"),
                "name": data.get("name", "Unknown Token"),
                "decimals": 9,
                "creator": data.get("creator", "")
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
                "source": "DexScreener"
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
                        "source": "DexScreenerProfiles"
                    })
        return tokens

    def get_token_security_data(self, mint: str) -> Optional[Dict[str, Any]]:
        # DexScreener doesn't expose mint authorities directly
        return None

    def get_recent_trades(self, mint: str, limit: int = 50) -> List[Dict[str, Any]]:
        return []
