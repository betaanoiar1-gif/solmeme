"""
Resilient Solana RPC client with dynamic failover, rate limiting, and endpoint health tracking.
"""

from dataclasses import dataclass
import json
import logging
import time
from typing import Any, Dict, List, Optional
import urllib.error
import urllib.request

logger = logging.getLogger("meme_alpha_hunter.rpc")


@dataclass
class EndpointHealth:
    url: str
    total_requests: int = 0
    successful_requests: int = 0
    consecutive_errors: int = 0
    last_error_time: float = 0.0
    cooldown_until: float = 0.0
    avg_latency_ms: float = 0.0
    is_active: bool = True


class SolanaRPCClient:
    def __init__(self, endpoints: Optional[List[str]] = None, timeout: float = 2.0, max_retries: int = 3):
        self.endpoints_list = endpoints or [
            "https://api.mainnet-beta.solana.com",
            "https://solana-mainnet.rpc.extrnode.com",
            "https://rpc.ankr.com/solana",
            "https://solana.public-rpc.com"
        ]
        self.health: Dict[str, EndpointHealth] = {
            url: EndpointHealth(url=url) for url in self.endpoints_list
        }
        self.current_endpoint_idx = 0
        self.timeout = timeout
        self.max_retries = max_retries
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl_sec = 5.0
        self._last_call_ts = 0.0
        self._min_interval_sec = 0.1  # Rate limiting

    def _get_available_endpoint(self) -> Optional[str]:
        now = time.time()
        # First try active endpoints not in cooldown
        for i in range(len(self.endpoints_list)):
            idx = (self.current_endpoint_idx + i) % len(self.endpoints_list)
            url = self.endpoints_list[idx]
            ep_health = self.health[url]
            if ep_health.cooldown_until <= now:
                self.current_endpoint_idx = idx
                return url

        # If all in cooldown, pick the one with oldest error time
        sorted_eps = sorted(self.endpoints_list, key=lambda u: self.health[u].last_error_time)
        return sorted_eps[0] if sorted_eps else None

    def _record_success(self, url: str, latency_ms: float):
        ep = self.health[url]
        ep.total_requests += 1
        ep.successful_requests += 1
        ep.consecutive_errors = 0
        ep.avg_latency_ms = (ep.avg_latency_ms * 0.8) + (latency_ms * 0.2)
        ep.is_active = True

    def _record_failure(self, url: str):
        now = time.time()
        ep = self.health[url]
        ep.total_requests += 1
        ep.consecutive_errors += 1
        ep.last_error_time = now
        # Exponential cooldown: 5s, 15s, 45s up to 120s
        cooldown_sec = min(5.0 * (2 ** (ep.consecutive_errors - 1)), 120.0)
        ep.cooldown_until = now + cooldown_sec
        logger.debug(f"RPC endpoint {url} failed ({ep.consecutive_errors} consecutive errors). Cooling down for {cooldown_sec:.1f}s")
        # Rotate index
        self.current_endpoint_idx = (self.current_endpoint_idx + 1) % len(self.endpoints_list)

    def call(self, method: str, params: Optional[List[Any]] = None, use_cache: bool = True) -> Optional[Dict[str, Any]]:
        params = params or []
        cache_key = f"{method}:{json.dumps(params)}"

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
            endpoint = self._get_available_endpoint()
            if not endpoint:
                break

            # Rate limiting check
            elapsed = time.time() - self._last_call_ts
            if elapsed < self._min_interval_sec:
                time.sleep(self._min_interval_sec - elapsed)
            self._last_call_ts = time.time()

            t0 = time.time()
            try:
                req = urllib.request.Request(
                    endpoint,
                    data=data_bytes,
                    headers={"Content-Type": "application/json", "User-Agent": "MemeAlphaHunter/1.0"}
                )
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    latency_ms = (time.time() - t0) * 1000.0
                    res_json = json.loads(resp.read().decode("utf-8"))
                    if "result" in res_json:
                        self._record_success(endpoint, latency_ms)
                        if use_cache:
                            self._cache[cache_key] = {"ts": time.time(), "data": res_json["result"]}
                        return res_json["result"]
                    elif "error" in res_json:
                        logger.warning(f"RPC {endpoint} returned JSON-RPC error: {res_json['error']}")
                        self._record_failure(endpoint)
            except Exception as e:
                logger.debug(f"RPC call attempt {attempt+1} failed on {endpoint}: {e}")
                self._record_failure(endpoint)
                time.sleep(0.1 * (2 ** attempt))

        return None

    def get_token_supply(self, mint: str) -> Optional[float]:
        res = self.call("getTokenSupply", [mint])
        if res and "value" in res and "uiAmount" in res["value"]:
            return float(res["value"]["uiAmount"])
        return None

    def get_account_info(self, pubkey: str, encoding: str = "jsonParsed") -> Optional[Dict[str, Any]]:
        res = self.call("getAccountInfo", [pubkey, {"encoding": encoding}])
        if res and isinstance(res, dict):
            return res
        return None

    def get_health(self) -> Optional[str]:
        res = self.call("getHealth")
        return res if isinstance(res, str) else ("ok" if res is not None else None)

    def get_signatures_for_address(self, address: str, limit: int = 25) -> Optional[List[Dict[str, Any]]]:
        res = self.call("getSignaturesForAddress", [address, {"limit": limit}])
        return res if isinstance(res, list) else None

    def get_transaction(self, signature: str, encoding: str = "jsonParsed") -> Optional[Dict[str, Any]]:
        res = self.call("getTransaction", [signature, {"encoding": encoding, "maxSupportedTransactionVersion": 0}])
        return res if isinstance(res, dict) else None

    def get_token_largest_accounts(self, mint: str) -> Optional[List[Dict[str, Any]]]:
        res = self.call("getTokenLargestAccounts", [mint])
        if res and isinstance(res, dict) and "value" in res:
            return res["value"]
        return None

    def get_health_metrics(self) -> Dict[str, Any]:
        return {
            url: {
                "total_requests": h.total_requests,
                "successful_requests": h.successful_requests,
                "consecutive_errors": h.consecutive_errors,
                "is_active": h.is_active,
                "in_cooldown": h.cooldown_until > time.time()
            }
            for url, h in self.health.items()
        }
