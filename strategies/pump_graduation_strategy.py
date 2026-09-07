"""Pump.fun -> DEX graduation paper strategy.

Research objective:
- discover Pump.fun coins while they are still on the bonding curve;
- rank candidates using only observable pre-graduation evidence;
- paper-enter before graduation;
- exit once Pump.fun reports graduation and a DEX pair is observable.

No live-money execution is included. The strategy is intentionally separate from
MEME ALPHA HUNTER's generic scorer so its results can be compared honestly.
"""

from dataclasses import dataclass
import time
from typing import Any, Dict, List, Optional
import urllib.parse
import urllib.request
import json


PUMP_API_V1 = "https://frontend-api.pump.fun"
PUMP_API_V3 = "https://frontend-api-v3.pump.fun"
TOTAL_SUPPLY = 1_000_000_000_000_000
INITIAL_VIRTUAL_TOKEN_RESERVES = 1_073_000_000_000_000
# Current protocol guidance documents the bonding-curve state and graduation event;
# this value is used only to form a proximity estimate, while `complete` remains the
# authoritative graduation trigger.
APPROX_NEAR_GRADUATION_VIRTUAL_TOKENS = 206_900_000_000_000


@dataclass
class GraduationCandidate:
    mint: str
    symbol: str
    name: str
    creator: str
    age_minutes: float
    market_cap_usd: Optional[float]
    price_usd: Optional[float]
    curve_progress_pct: Optional[float]
    reply_count: int
    last_trade_timestamp: Optional[float]
    has_socials: bool
    integrity_score: float
    activity_score: float
    graduation_score: float
    total_score: float
    complete: bool
    raw: Dict[str, Any]


@dataclass
class PaperGraduationTrade:
    mint: str
    symbol: str
    entry_price_usd: float
    entry_time: float
    exit_price_usd: Optional[float] = None
    exit_time: Optional[float] = None
    roi_pct: Optional[float] = None
    multiple: Optional[float] = None
    exit_reason: Optional[str] = None


class PumpGraduationStrategy:
    def __init__(self, timeout: float = 5.0):
        self.timeout = timeout
        self._cache: Dict[str, Dict[str, Any]] = {}

    def _get_json(self, url: str) -> Optional[Any]:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "MemeAlphaHunter-PumpGraduation/1.0", "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception:
            return None

    def latest_coins(self, limit: int = 50) -> List[Dict[str, Any]]:
        # V1 is publicly reachable on many deployments and is preferable here because
        # this experiment must not depend on an authenticated or paid data API.
        q = urllib.parse.urlencode({"offset": 0, "limit": min(limit, 100), "includeNsfw": "false"})
        data = self._get_json(f"{PUMP_API_V1}/coins?{q}")
        if isinstance(data, list):
            return data
        # Keep an explicit fallback for deployments exposing the newer per-coin API;
        # discovery remains fail-closed when no public launch list is available.
        data = self._get_json(f"{PUMP_API_V1}/coins/latest")
        return [data] if isinstance(data, dict) and data.get("mint") else []

    def coin(self, mint: str) -> Optional[Dict[str, Any]]:
        if mint in self._cache and time.time() - self._cache[mint]["ts"] < 2.0:
            return dict(self._cache[mint]["data"])
        data = self._get_json(f"{PUMP_API_V3}/coins-v2/{mint}")
        if not isinstance(data, dict):
            data = self._get_json(f"{PUMP_API_V1}/coins/{mint}")
        if isinstance(data, dict):
            self._cache[mint] = {"ts": time.time(), "data": dict(data)}
            return data
        return None

    @staticmethod
    def _num(value: Any) -> Optional[float]:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _socials(c: Dict[str, Any]) -> bool:
        return any(bool(c.get(k)) for k in ("twitter", "telegram", "website", "socials", "twitter_url", "telegram_url", "website_url"))

    def curve_progress_pct(self, c: Dict[str, Any]) -> Optional[float]:
        vt = self._num(c.get("virtual_token_reserves"))
        if vt is None:
            return None
        denom = INITIAL_VIRTUAL_TOKEN_RESERVES - APPROX_NEAR_GRADUATION_VIRTUAL_TOKENS
        progress = ((INITIAL_VIRTUAL_TOKEN_RESERVES - vt) / max(denom, 1.0)) * 100.0
        return max(0.0, min(100.0, progress))

    def build_candidate(self, coin: Dict[str, Any], now: Optional[float] = None) -> Optional[GraduationCandidate]:
        now = now or time.time()
        mint = coin.get("mint")
        if not mint or bool(coin.get("complete")):
            return None
        created = self._num(coin.get("created_timestamp"))
        if created is None:
            created = self._num(coin.get("created_at"))
        if created is None:
            return None
        if created > 10_000_000_000:
            created /= 1000.0
        age_minutes = max(0.0, (now - created) / 60.0)
        if age_minutes > 180.0:
            return None

        market_cap = self._num(coin.get("usd_market_cap"))
        if market_cap is None:
            market_cap = self._num(coin.get("market_cap"))
            if market_cap and market_cap > 1_000_000_000:
                market_cap /= 1_000_000.0

        price = None
        if market_cap is not None:
            price = market_cap / TOTAL_SUPPLY

        replies = int(self._num(coin.get("reply_count")) or 0)
        last_trade = self._num(coin.get("last_trade_timestamp"))
        if last_trade and last_trade > 10_000_000_000:
            last_trade /= 1000.0

        progress = self.curve_progress_pct(coin)
        has_socials = self._socials(coin)

        # Integrity is deliberately conservative: missing evidence receives no
        # fabricated points. A revoked authority is stronger evidence than metadata.
        integrity = 45.0
        if coin.get("mint_authority") in (None, "", False):
            integrity += 15.0
        if coin.get("freeze_authority") in (None, "", False):
            integrity += 15.0
        if has_socials:
            integrity += 10.0
        integrity = min(100.0, integrity)

        recency = 0.0
        if last_trade is not None:
            age_trade = max(0.0, (now - last_trade) / 60.0)
            recency = max(0.0, min(100.0, 100.0 - age_trade * 20.0))
        reply_component = min(100.0, replies * 5.0)
        activity = (recency * 0.65) + (reply_component * 0.35)

        grad = progress if progress is not None else 0.0
        if progress is None:
            grad = 20.0 if market_cap is not None and market_cap >= 30_000 else 0.0

        total = integrity * 0.35 + activity * 0.30 + grad * 0.35
        return GraduationCandidate(
            mint=mint,
            symbol=str(coin.get("symbol") or "UNKNOWN"),
            name=str(coin.get("name") or "Solana Token"),
            creator=str(coin.get("creator") or ""),
            age_minutes=round(age_minutes, 2),
            market_cap_usd=market_cap,
            price_usd=price,
            curve_progress_pct=progress,
            reply_count=replies,
            last_trade_timestamp=last_trade,
            has_socials=has_socials,
            integrity_score=round(integrity, 2),
            activity_score=round(activity, 2),
            graduation_score=round(grad, 2),
            total_score=round(total, 2),
            complete=False,
            raw=dict(coin),
        )

    def rank(self, limit: int = 10) -> List[GraduationCandidate]:
        candidates: List[GraduationCandidate] = []
        for coin in self.latest_coins(limit=max(limit * 3, 30)):
            c = self.build_candidate(coin)
            if c:
                candidates.append(c)
        candidates.sort(key=lambda x: x.total_score, reverse=True)
        return candidates[:limit]

    def wait_for_graduation(self, mint: str, timeout_seconds: float = 300.0, interval_seconds: float = 3.0) -> Optional[Dict[str, Any]]:
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            state = self.coin(mint)
            if state and bool(state.get("complete")):
                return state
            time.sleep(interval_seconds)
        return None
