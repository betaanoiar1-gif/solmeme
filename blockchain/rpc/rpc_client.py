"""
Resilient, rate-limited, and cached Solana RPC client.
"""

import json
import logging
import time
from typing import Any, Dict, List, Optional
import urllib.error
import urllib.request

logger = logging.getLogger("meme_alpha_hunter.rpc")


class SolanaRPCClient:
    def __init__(self, endpoints: Optional[List[str]] = None, timeout: float = 0.5, max_retries: int = 1):
        self.endpoints = endpoints or [
            "https://api.mainnet-beta.solana.com",
            "https://solana-mainnet.rpc.extrnode.com",
            "https://rpc.ankr.com/solana"
        ]
        self.current_endpoint_idx = 0
        self.timeout = timeout
        self.max_retries = max_retries
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl_sec = 5.0
        self._last_call_ts = 0.0
        self._min_interval_sec = 0.05  # 20 req/sec max rate limit
        self._network_available = True

    @property
    def current_endpoint(self) -> str:
        return self.endpoints[self.current_endpoint_idx % len(self.endpoints)]

    def _rotate_endpoint(self):
        self.current_endpoint_idx = (self.current_endpoint_idx + 1) % len(self.endpoints)
        logger.warning(f"Switched RPC endpoint to: {self.current_endpoint}")

    def call(self, method: str, params: Optional[List[Any]] = None, use_cache: bool = True) -> Optional[Dict[str, Any]]:
        if not self._network_available:
            return None

        params = params or []
        cache_key = f"{method}:{json.dumps(params)}"

        # Check in-memory cache
        if use_cache and cache_key in self._cache:
            entry = self._cache[cache_key]
            if time.time() - entry["ts"] < self._cache_ttl_sec:
                return entry["data"]

        payload = {
            "jsonrpc": "2.0",
            "id": int(time.time() * 1000),
            "method": method,
            "params": params
        }
        data_bytes = json.dumps(payload).encode("utf-8")

        for attempt in range(self.max_retries):
            # Rate limiting
            elapsed = time.time() - self._last_call_ts
            if elapsed < self._min_interval_sec:
                time.sleep(self._min_interval_sec - elapsed)
            self._last_call_ts = time.time()

            try:
                req = urllib.request.Request(
                    self.current_endpoint,
                    data=data_bytes,
                    headers={"Content-Type": "application/json", "User-Agent": "MemeAlphaHunter/1.0"}
                )
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    res_json = json.loads(resp.read().decode("utf-8"))
                    if "result" in res_json:
                        if use_cache:
                            self._cache[cache_key] = {"ts": time.time(), "data": res_json["result"]}
                        return res_json["result"]
                    elif "error" in res_json:
                        logger.warning(f"RPC returned error: {res_json['error']}")
            except Exception as e:
                logger.debug(f"RPC call attempt {attempt+1} failed on {self.current_endpoint}: {e}")
                self._rotate_endpoint()
                self._network_available = False
                break

        return None

    def get_token_supply(self, mint: str) -> Optional[float]:
        res = self.call("getTokenSupply", [mint])
        if res and "value" in res and "uiAmount" in res["value"]:
            return float(res["value"]["uiAmount"])
        return None

    def get_account_info(self, pubkey: str) -> Optional[Dict[str, Any]]:
        res = self.call("getAccountInfo", [pubkey, {"encoding": "jsonParsed"}])
        if res and "value" in res:
            return res["value"]
        return None
