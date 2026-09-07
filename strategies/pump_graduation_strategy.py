"""Pump.fun pre-graduation -> DEX paper strategy.

The strategy discovers active Pump.fun launches before graduation, ranks them only
from observable public evidence, paper-enters the strongest candidates, and exits
at the first real Solana DEX quote observed after Pump.fun completion.

PAPER ONLY: no wallet, private key, signing, or order submission.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import time
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

PUMP_API = "https://frontend-api.pump.fun"
DEX_API = "https://api.dexscreener.com/latest/dex/tokens"
PUMP_PROGRAM_ID = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
TOTAL_SUPPLY_BASE_UNITS = 1_000_000_000_000_000
INITIAL_VIRTUAL_TOKEN_RESERVES = 1_073_000_000_000_000
INITIAL_REAL_TOKEN_RESERVES = 793_100_000_000_000


@dataclass
class GraduationCandidate:
    mint: str
    symbol: str
    name: str
    creator: str
    age_minutes: float
    price_usd: Optional[float]
    market_cap_usd: Optional[float]
    curve_progress_pct: Optional[float]
    buy_share_pct: Optional[float]
    buy_trades: int
    sell_trades: int
    unique_buyers: int
    trade_volume_sol: float
    last_trade_timestamp: Optional[float]
    has_socials: bool
    mint_authority_revoked: Optional[bool]
    freeze_authority_revoked: Optional[bool]
    integrity_score: float
    activity_score: float
    graduation_score: float
    total_score: float
    observed_at: float
    raw: Dict[str, Any]


@dataclass
class PaperGraduationTrade:
    mint: str
    symbol: str
    entry_price_usd: float
    entry_time: float
    position_value_usd: float
    quantity: float
    entry_score: float
    curve_progress_pct: Optional[float]
    status: str = "PAPER_HOLDING"
    graduation_time: Optional[float] = None
    exit_time: Optional[float] = None
    exit_price_usd: Optional[float] = None
    multiple: Optional[float] = None
    roi_pct: Optional[float] = None
    exit_reason: Optional[str] = None
    dex: Optional[str] = None
    dex_pair: Optional[str] = None


class PumpGraduationStrategy:
    def __init__(self, timeout: float = 6.0):
        self.timeout = timeout
        self._coin_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}
        self._trade_cache: Dict[str, Tuple[float, List[Dict[str, Any]]]] = {}
        self._last_api_error: Optional[str] = None

    @staticmethod
    def _as_list(data: Any) -> List[Dict[str, Any]]:
        if isinstance(data, list):
            return [x for x in data if isinstance(x, dict)]
        if isinstance(data, dict):
            for key in ("data", "result", "coins", "trades", "items"):
                value = data.get(key)
                if isinstance(value, list):
                    return [x for x in value if isinstance(x, dict)]
            return [data]
        return []

    def _get_json(self, url: str) -> Optional[Any]:
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "MemeAlphaHunter-PumpGraduation/3.0",
                    "Accept": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            self._last_api_error = f"{type(exc).__name__}: {exc}"
            return None

    @staticmethod
    def _num(value: Any) -> Optional[float]:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _ts(value: Any) -> Optional[float]:
        number = PumpGraduationStrategy._num(value)
        if number is None:
            return None
        return number / 1000.0 if number > 10_000_000_000 else number

    @staticmethod
    def _socials(coin: Dict[str, Any]) -> bool:
        return any(bool(coin.get(k)) for k in (
            "twitter", "telegram", "website", "socials",
            "twitter_url", "telegram_url", "website_url",
        ))

    def latest_coins(self, limit: int = 50) -> List[Dict[str, Any]]:
        query = urllib.parse.urlencode({
            "offset": 0,
            "limit": min(max(limit, 20), 100),
            "includeNsfw": "false",
        })
        data = self._get_json(f"{PUMP_API}/coins?{query}")
        coins = self._as_list(data)
        if coins:
            return coins
        return self._as_list(self._get_json(f"{PUMP_API}/coins/latest"))

    def latest_trade(self) -> Optional[Dict[str, Any]]:
        values = self._as_list(self._get_json(f"{PUMP_API}/trades/latest"))
        if not values:
            return None
        trade = dict(values[0])
        mint = trade.get("mint") or trade.get("tokenMint")
        if mint:
            trade["mint"] = mint
        return trade if trade.get("mint") else None

    def coin(self, mint: str, cache_seconds: float = 3.0) -> Optional[Dict[str, Any]]:
        now = time.time()
        cached = self._coin_cache.get(mint)
        if cached and now - cached[0] < cache_seconds:
            return dict(cached[1])
        for url in (
            f"{PUMP_API}/coins/{mint}",
            f"https://frontend-api-v3.pump.fun/coins-v2/{mint}",
        ):
            data = self._get_json(url)
            values = self._as_list(data)
            if values:
                candidate = dict(values[0])
                candidate.setdefault("mint", mint)
                if candidate.get("mint") == mint:
                    self._coin_cache[mint] = (now, candidate)
                    return candidate
            if isinstance(data, dict) and (data.get("mint") == mint or data.get("address") == mint):
                candidate = dict(data)
                candidate.setdefault("mint", mint)
                self._coin_cache[mint] = (now, candidate)
                return candidate
        return None

    def trades(self, mint: str, limit: int = 50, cache_seconds: float = 10.0) -> List[Dict[str, Any]]:
        now = time.time()
        cached = self._trade_cache.get(mint)
        if cached and now - cached[0] < cache_seconds:
            return [dict(x) for x in cached[1]]
        query = urllib.parse.urlencode({"limit": min(max(limit, 5), 100), "offset": 0, "minimumSize": 0})
        values = self._as_list(self._get_json(f"{PUMP_API}/trades/all/{mint}?{query}"))
        self._trade_cache[mint] = (now, [dict(x) for x in values])
        return values

    def curve_progress_pct(self, coin: Dict[str, Any]) -> Optional[float]:
        real = self._num(coin.get("real_token_reserves"))
        if real is not None:
            return max(0.0, min(100.0, 100.0 * (1.0 - real / INITIAL_REAL_TOKEN_RESERVES)))
        virtual = self._num(coin.get("virtual_token_reserves"))
        if virtual is not None:
            denom = max(INITIAL_VIRTUAL_TOKEN_RESERVES - 206_900_000_000_000, 1.0)
            return max(0.0, min(100.0, 100.0 * (INITIAL_VIRTUAL_TOKEN_RESERVES - virtual) / denom))
        return None

    def _trade_stats(self, mint: str) -> Tuple[int, int, int, float, Optional[float]]:
        buys = sells = 0
        buyers = set()
        volume_sol = 0.0
        latest_ts: Optional[float] = None
        for trade in self.trades(mint):
            kind = str(trade.get("txType") or trade.get("type") or trade.get("side") or "").lower()
            is_buy = trade.get("isBuy")
            if isinstance(is_buy, str):
                is_buy = is_buy.lower() == "true"
            if is_buy is True or kind in {"buy", "create"}:
                buys += 1
                user = trade.get("user") or trade.get("trader") or trade.get("owner")
                if user:
                    buyers.add(str(user))
            elif is_buy is False or kind == "sell":
                sells += 1
            sol = self._num(trade.get("solAmount") or trade.get("sol_amount"))
            if sol is not None:
                volume_sol += sol / 1_000_000_000 if sol > 10_000_000 else sol
            ts = self._ts(trade.get("timestamp") or trade.get("blockTime") or trade.get("created_timestamp"))
            if ts is not None:
                latest_ts = ts if latest_ts is None else max(latest_ts, ts)
        return buys, sells, len(buyers), volume_sol, latest_ts

    def build_candidate(self, coin: Dict[str, Any], now: Optional[float] = None) -> Optional[GraduationCandidate]:
        now = now or time.time()
        mint = coin.get("mint")
        if not mint or bool(coin.get("complete")):
            return None
        created = self._ts(coin.get("created_timestamp") or coin.get("created_at"))
        if created is None:
            return None
        age = max(0.0, (now - created) / 60.0)
        if age > 180.0:
            return None

        market_cap = self._num(coin.get("usd_market_cap") or coin.get("market_cap"))
        price = self._num(coin.get("price_usd") or coin.get("priceUsd"))
        if price is None and market_cap is not None:
            price = market_cap / TOTAL_SUPPLY_BASE_UNITS
        if price is None or price <= 0:
            return None

        progress = self.curve_progress_pct(coin)
        buys, sells, unique_buyers, volume_sol, last_trade = self._trade_stats(str(mint))
        total = buys + sells
        buy_share = 100.0 * buys / total if total else None
        fallback_last = self._ts(coin.get("last_trade_timestamp"))
        effective_last = last_trade or fallback_last
        recency = 0.0
        if effective_last is not None:
            recency = max(0.0, min(100.0, 100.0 - max(0.0, (now - effective_last) / 60.0) * 25.0))
        flow = 50.0 if buy_share is None else buy_share
        breadth = min(100.0, unique_buyers / 20.0 * 100.0)
        activity = recency * 0.35 + flow * 0.45 + breadth * 0.20

        mint_revoked: Optional[bool] = None
        freeze_revoked: Optional[bool] = None
        integrity = 45.0
        if "mint_authority" in coin:
            mint_revoked = coin.get("mint_authority") in (None, "", False)
            if mint_revoked:
                integrity += 20.0
        if "freeze_authority" in coin:
            freeze_revoked = coin.get("freeze_authority") in (None, "", False)
            if freeze_revoked:
                integrity += 20.0
        if self._socials(coin):
            integrity += 10.0
        integrity = min(100.0, integrity)
        graduation = progress if progress is not None else 20.0
        score = integrity * 0.35 + activity * 0.35 + graduation * 0.30

        return GraduationCandidate(
            mint=str(mint),
            symbol=str(coin.get("symbol") or "UNKNOWN"),
            name=str(coin.get("name") or "Solana Token"),
            creator=str(coin.get("creator") or ""),
            age_minutes=round(age, 2),
            price_usd=round(price, 12),
            market_cap_usd=market_cap,
            curve_progress_pct=round(progress, 2) if progress is not None else None,
            buy_share_pct=round(buy_share, 2) if buy_share is not None else None,
            buy_trades=buys,
            sell_trades=sells,
            unique_buyers=unique_buyers,
            trade_volume_sol=round(volume_sol, 6),
            last_trade_timestamp=effective_last,
            has_socials=self._socials(coin),
            mint_authority_revoked=mint_revoked,
            freeze_authority_revoked=freeze_revoked,
            integrity_score=round(integrity, 2),
            activity_score=round(activity, 2),
            graduation_score=round(graduation, 2),
            total_score=round(score, 2),
            observed_at=now,
            raw=dict(coin),
        )

    def discover(self, limit: int = 50, probe_limit: int = 15) -> List[GraduationCandidate]:
        coins = self.latest_coins(limit=limit)
        latest = self.latest_trade()
        if latest and latest.get("mint") and not any(str(c.get("mint")) == str(latest["mint"]) for c in coins):
            coins.insert(0, latest)
        now = time.time()
        coarse = []
        for coin in coins:
            mint = coin.get("mint")
            created = self._ts(coin.get("created_timestamp") or coin.get("created_at"))
            if not mint or bool(coin.get("complete")) or created is None:
                continue
            age = max(0.0, (now - created) / 60.0)
            if age > 180.0:
                continue
            progress = self.curve_progress_pct(coin) or 0.0
            last = self._ts(coin.get("last_trade_timestamp"))
            recency = max(0.0, 100.0 - max(0.0, (now - last) / 60.0) * 25.0) if last else 0.0
            priority = progress * 0.60 + recency * 0.25 + max(0.0, 100.0 - age) * 0.15
            coarse.append((priority, coin))
        coarse.sort(key=lambda x: x[0], reverse=True)

        candidates: List[GraduationCandidate] = []
        seen = set()
        for _, raw in coarse[: max(1, min(probe_limit, 25))]:
            mint = str(raw.get("mint"))
            if mint in seen:
                continue
            seen.add(mint)
            detailed = self.coin(mint) or raw
            candidate = self.build_candidate(detailed, now=now)
            if candidate:
                candidates.append(candidate)
        candidates.sort(key=lambda x: x.total_score, reverse=True)
        return candidates

    def first_dex_quote(self, mint: str) -> Optional[Dict[str, Any]]:
        data = self._get_json(f"{DEX_API}/{mint}")
        if not isinstance(data, dict):
            return None
        pairs = [p for p in data.get("pairs", []) if isinstance(p, dict) and p.get("chainId") == "solana" and p.get("priceUsd") is not None]
        if not pairs:
            return None
        pairs.sort(key=lambda p: (float(p.get("pairCreatedAt") or 0.0), -float(((p.get("liquidity") or {}).get("usd")) or 0.0)))
        pair = pairs[0]
        try:
            price = float(pair["priceUsd"])
        except (TypeError, ValueError):
            return None
        return {
            "price": price,
            "dex": pair.get("dexId"),
            "pair": pair.get("pairAddress"),
            "created_at": float(pair["pairCreatedAt"]) / 1000.0 if pair.get("pairCreatedAt") else None,
        }

    def last_api_error(self) -> Optional[str]:
        return self._last_api_error
