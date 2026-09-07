"""Pump.fun pre-graduation -> DEX paper strategy.

The strategy is intentionally separate from the general live paper engine.
It listens to PumpPortal's free new-token and migration streams on ONE
WebSocket connection. It enters paper positions on selected Pump.fun launches
and closes them on the first observed DEX market quote after migration.

No private keys, no real execution, no trade-stream subscription, no paid API.
"""

from __future__ import annotations

import csv
import json
import math
import os
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import requests
import websocket


PUMP_WS = "wss://pumpportal.fun/api/data"
DEX_TOKEN_URL = "https://api.dexscreener.com/latest/dex/tokens/{}"
SOL_PRICE_URL = "https://api.dexscreener.com/latest/dex/tokens/So11111111111111111111111111111111111111112"


@dataclass
class Candidate:
    mint: str
    symbol: str
    name: str
    creator: str
    created_at: float
    market_cap_sol: Optional[float]
    initial_buy_tokens: Optional[float]
    sol_amount: Optional[float]
    v_sol: Optional[float]
    v_tokens: Optional[float]
    uri: Optional[str]
    score: float
    entry_price_sol: Optional[float]
    entry_price_usd: Optional[float]
    status: str = "WATCH"
    entry_time: Optional[float] = None
    exit_time: Optional[float] = None
    exit_price_usd: Optional[float] = None
    multiple: Optional[float] = None
    reason: str = ""


@dataclass
class StrategyStats:
    observed_launches: int = 0
    eligible_candidates: int = 0
    paper_entries: int = 0
    migrations_seen: int = 0
    paper_exits: int = 0
    no_dex_quote: int = 0
    peak_multiple: float = 0.0
    max_50x_candidates: int = 0
    duplicate_creators: int = 0
    rejected_spam_or_weak: int = 0


class PumpFunGraduationStrategy:
    """Paper strategy: select strong Pump.fun launches, sell at first DEX quote."""

    def __init__(self, duration_minutes: float = 5.0, capital_usd: float = 100.0, per_trade_usd: float = 5.0):
        self.duration_sec = duration_minutes * 60.0
        self.capital_usd = float(capital_usd)
        self.per_trade_usd = float(per_trade_usd)
        self.cash_usd = self.capital_usd
        self.candidates: Dict[str, Candidate] = {}
        self.creator_counts: Dict[str, int] = {}
        self.stats = StrategyStats()
        self.ws: Optional[websocket.WebSocket] = None
        self.events: List[dict] = []
        self.sol_price_usd: Optional[float] = None

    @staticmethod
    def _safe_float(value) -> Optional[float]:
        try:
            return float(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    def refresh_sol_price(self) -> Optional[float]:
        try:
            r = requests.get(SOL_PRICE_URL, timeout=3)
            data = r.json()
            pairs = data.get("pairs") or []
            solana = [p for p in pairs if p.get("chainId") == "solana"]
            if solana:
                pair = max(solana, key=lambda p: float(((p.get("liquidity") or {}).get("usd")) or 0.0))
            elif pairs:
                pair = max(pairs, key=lambda p: float(((p.get("liquidity") or {}).get("usd")) or 0.0))
            else:
                return self.sol_price_usd
            price = self._safe_float(pair.get("priceUsd"))
            if price and price > 0:
                self.sol_price_usd = price
        except Exception:
            pass
        return self.sol_price_usd

    @staticmethod
    def initial_price_sol(v_sol: Optional[float], v_tokens: Optional[float]) -> Optional[float]:
        if v_sol is None or v_tokens is None or v_sol <= 0 or v_tokens <= 0:
            return None
        return v_sol / v_tokens

    def score_launch(self, msg: dict) -> tuple[float, str]:
        """Evidence-only launch score; no fabricated holder/wallet metrics."""
        score = 0.0
        reasons: List[str] = []
        mcap = self._safe_float(msg.get("marketCapSol"))
        initial_buy = self._safe_float(msg.get("solAmount"))
        name = str(msg.get("name") or "").strip()
        symbol = str(msg.get("symbol") or "").strip()
        creator = str(msg.get("traderPublicKey") or "").strip()
        uri = str(msg.get("uri") or "").strip()

        # 30 points: meaningful creator initial buy without chasing a huge initial cap.
        if initial_buy is not None:
            if 0.5 <= initial_buy <= 2.5:
                score += 30.0
                reasons.append("healthy_initial_buy")
            elif 0.2 <= initial_buy < 0.5 or 2.5 < initial_buy <= 5.0:
                score += 18.0
                reasons.append("moderate_initial_buy")
            elif initial_buy > 5.0:
                score += 6.0
                reasons.append("oversized_initial_buy")

        # 25 points: enter early, but avoid obvious already-expensive launches.
        if mcap is not None:
            if 25.0 <= mcap <= 40.0:
                score += 25.0
                reasons.append("early_curve_cap")
            elif 40.0 < mcap <= 60.0:
                score += 14.0
                reasons.append("later_curve_cap")
            elif mcap < 25.0:
                score += 18.0
                reasons.append("very_early_cap")
            else:
                score += 4.0
                reasons.append("high_initial_cap")

        # 20 points: metadata completeness as an anti-shill/anti-noise signal.
        quality = 0.0
        if 2 <= len(name) <= 40:
            quality += 6.0
        if 2 <= len(symbol) <= 15:
            quality += 5.0
        if uri:
            quality += 4.0
        if msg.get("website") or msg.get("twitter") or msg.get("telegram"):
            quality += 5.0
        score += quality
        if quality >= 15:
            reasons.append("metadata_complete")
        elif quality < 8:
            reasons.append("metadata_weak")

        # 25 points: creator novelty within this live observation window.
        prior = self.creator_counts.get(creator, 0)
        if creator and prior == 0:
            score += 20.0
            reasons.append("creator_first_seen")
        elif creator and prior == 1:
            score += 8.0
            reasons.append("creator_repeat_once")
        else:
            score += 0.0
            reasons.append("creator_repeated")

        # Strong minimum so the system does not fill the $100 paper wallet with noise.
        return round(min(score, 100.0), 2), ",".join(reasons)

    def accept_launch(self, msg: dict) -> Optional[Candidate]:
        mint = str(msg.get("mint") or "").strip()
        if not mint or mint in self.candidates:
            return None
        score, reason = self.score_launch(msg)
        creator = str(msg.get("traderPublicKey") or "").strip()
        prior = self.creator_counts.get(creator, 0)
        self.creator_counts[creator] = prior + 1
        if prior > 0:
            self.stats.duplicate_creators += 1

        self.stats.observed_launches += 1
        if score < 60.0:
            self.stats.rejected_spam_or_weak += 1
            return None

        v_sol = self._safe_float(msg.get("vSolInBondingCurve"))
        v_tokens = self._safe_float(msg.get("vTokensInBondingCurve"))
        entry_sol = self.initial_price_sol(v_sol, v_tokens)
        if entry_sol is None:
            self.stats.rejected_spam_or_weak += 1
            return None

        self.refresh_sol_price()
        entry_usd = entry_sol * self.sol_price_usd if self.sol_price_usd else None
        candidate = Candidate(
            mint=mint,
            symbol=str(msg.get("symbol") or "UNKNOWN"),
            name=str(msg.get("name") or "Unknown"),
            creator=creator,
            created_at=time.time(),
            market_cap_sol=self._safe_float(msg.get("marketCapSol")),
            initial_buy_tokens=self._safe_float(msg.get("initialBuy")),
            sol_amount=self._safe_float(msg.get("solAmount")),
            v_sol=v_sol,
            v_tokens=v_tokens,
            uri=str(msg.get("uri")) if msg.get("uri") else None,
            score=score,
            entry_price_sol=entry_sol,
            entry_price_usd=entry_usd,
            status="PAPER_ENTRY",
            entry_time=time.time(),
            reason=reason,
        )
        self.candidates[mint] = candidate
        self.stats.eligible_candidates += 1
        if self.cash_usd >= self.per_trade_usd:
            self.cash_usd -= self.per_trade_usd
            self.stats.paper_entries += 1
            self._log("ENTRY", candidate)
        return candidate

    def dex_first_quote(self, mint: str) -> Optional[float]:
        try:
            r = requests.get(DEX_TOKEN_URL.format(mint), timeout=3)
            data = r.json()
            pairs = [p for p in (data.get("pairs") or []) if p.get("chainId") == "solana"]
            if not pairs:
                return None
            pair = max(pairs, key=lambda p: float(((p.get("liquidity") or {}).get("usd")) or 0.0))
            price = self._safe_float(pair.get("priceUsd"))
            return price if price and price > 0 else None
        except Exception:
            return None

    def handle_migration(self, msg: dict) -> None:
        mint = str(msg.get("mint") or "").strip()
        self.stats.migrations_seen += 1
        candidate = self.candidates.get(mint)
        if not candidate or candidate.status != "PAPER_ENTRY":
            return
        exit_usd = self.dex_first_quote(mint)
        if exit_usd is None:
            self.stats.no_dex_quote += 1
            candidate.reason += ",migration_seen_no_dex_quote"
            return

        candidate.exit_time = time.time()
        candidate.exit_price_usd = exit_usd
        if candidate.entry_price_usd and candidate.entry_price_usd > 0:
            candidate.multiple = exit_usd / candidate.entry_price_usd
        else:
            candidate.multiple = None
        candidate.status = "PAPER_EXIT"
        self.stats.paper_exits += 1
        if candidate.multiple is not None:
            self.stats.peak_multiple = max(self.stats.peak_multiple, candidate.multiple)
            if candidate.multiple >= 50.0:
                self.stats.max_50x_candidates += 1
        self.cash_usd += self.per_trade_usd * (candidate.multiple or 0.0)
        self._log("EXIT", candidate)

    def _log(self, event: str, candidate: Candidate) -> None:
        self.events.append({
            "timestamp": time.time(),
            "event": event,
            "mint": candidate.mint,
            "symbol": candidate.symbol,
            "score": candidate.score,
            "entry_usd": candidate.entry_price_usd,
            "exit_usd": candidate.exit_price_usd,
            "multiple": candidate.multiple,
            "reason": candidate.reason,
        })
        print(
            f"[{event}] {candidate.symbol} score={candidate.score:.1f} "
            f"entry=${candidate.entry_price_usd or 0:.8f} "
            f"exit=${candidate.exit_price_usd or 0:.8f} "
            f"multiple={candidate.multiple or 0:.2f}x"
        , flush=True)

    def write_reports(self, out_dir: str) -> None:
        os.makedirs(out_dir, exist_ok=True)
        with open(os.path.join(out_dir, "pumpfun_graduation_trades.csv"), "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "mint", "symbol", "name", "creator", "score", "market_cap_sol", "sol_amount",
                "entry_price_sol", "entry_price_usd", "exit_price_usd", "multiple", "status", "reason"
            ])
            writer.writeheader()
            for c in self.candidates.values():
                writer.writerow({
                    "mint": c.mint,
                    "symbol": c.symbol,
                    "name": c.name,
                    "creator": c.creator,
                    "score": c.score,
                    "market_cap_sol": c.market_cap_sol,
                    "sol_amount": c.sol_amount,
                    "entry_price_sol": c.entry_price_sol,
                    "entry_price_usd": c.entry_price_usd,
                    "exit_price_usd": c.exit_price_usd,
                    "multiple": c.multiple,
                    "status": c.status,
                    "reason": c.reason,
                })
        with open(os.path.join(out_dir, "pumpfun_graduation_events.json"), "w", encoding="utf-8") as f:
            json.dump({"stats": self.stats.__dict__, "events": self.events}, f, indent=2)

    def run(self, out_dir: str = "reports/pumpfun_strategy") -> None:
        start = time.time()
        self.refresh_sol_price()
        self.ws = websocket.create_connection(PUMP_WS, timeout=5)
        self.ws.send(json.dumps({"method": "subscribeNewToken"}))
        self.ws.send(json.dumps({"method": "subscribeMigration"}))
        print("PUMPFUN_STRATEGY_WS_CONNECTED", flush=True)
        print(f"PAPER_CAPITAL=${self.capital_usd:.2f} | PER_TRADE=${self.per_trade_usd:.2f}", flush=True)

        try:
            while time.time() - start < self.duration_sec:
                try:
                    raw = self.ws.recv()
                    if not raw:
                        continue
                    msg = json.loads(raw)
                except Exception:
                    continue

                tx_type = msg.get("txType")
                if tx_type == "create" and msg.get("mint"):
                    self.accept_launch(msg)
                elif msg.get("mint") and (msg.get("txType") in {"migration", "migrate"} or "pool" in msg):
                    self.handle_migration(msg)
        finally:
            try:
                self.ws.close()
            except Exception:
                pass
            self.write_reports(out_dir)
            print("=" * 72, flush=True)
            print("PUMPFUN GRADUATION STRATEGY — FINAL", flush=True)
            print(f"OBSERVED_LAUNCHES: {self.stats.observed_launches}", flush=True)
            print(f"ELIGIBLE_CANDIDATES: {self.stats.eligible_candidates}", flush=True)
            print(f"PAPER_ENTRIES: {self.stats.paper_entries}", flush=True)
            print(f"MIGRATIONS_SEEN: {self.stats.migrations_seen}", flush=True)
            print(f"PAPER_EXITS: {self.stats.paper_exits}", flush=True)
            print(f"NO_DEX_QUOTE: {self.stats.no_dex_quote}", flush=True)
            print(f"PEAK_MULTIPLE: {self.stats.peak_multiple:.2f}x", flush=True)
            print(f"50X_OR_MORE: {self.stats.max_50x_candidates}", flush=True)
            print(f"FINAL_PAPER_CASH: ${self.cash_usd:.2f}", flush=True)
            print("VERDICT: PUMPFUN_GRADUATION_STRATEGY_TESTED", flush=True)


if __name__ == "__main__":
    minutes = float(os.getenv("PUMPFUN_STRATEGY_MINUTES", "5"))
    PumpFunGraduationStrategy(duration_minutes=minutes).run()
