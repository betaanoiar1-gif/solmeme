"""Four-hour PAPER ONLY Pump.fun pre-graduation -> DEX experiment."""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import asdict
from typing import Any, Dict, List

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from strategies.pump_graduation_strategy import PaperGraduationTrade, PumpGraduationStrategy

INITIAL_CASH_USD = 100.0
MAX_POSITION_USD = 15.0
MAX_OPEN_POSITIONS = 5
ENTRY_SCORE_THRESHOLD = 60.0
MIN_BUY_TRADES_WHEN_AVAILABLE = 2
DISCOVERY_SECONDS = 10.0
POLL_SECONDS = 3.0
DEX_RETRY_SECONDS = 30.0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration-minutes", type=float, default=240.0)
    parser.add_argument("--output", default="reports/pump_graduation_strategy.json")
    parser.add_argument("--poll-seconds", type=float, default=POLL_SECONDS)
    args = parser.parse_args()

    strategy = PumpGraduationStrategy()
    started = time.time()
    deadline = started + max(1.0, args.duration_minutes * 60.0)
    cash = INITIAL_CASH_USD
    positions: Dict[str, PaperGraduationTrade] = {}
    completed: List[PaperGraduationTrade] = []
    discovered_mints = set()
    candidate_events: List[Dict[str, Any]] = []
    scans = 0
    api_errors = 0
    graduations_seen = 0
    dex_quotes_seen = 0
    max_multiple = None
    last_report_write = 0.0
    last_log = 0.0
    next_discovery = 0.0
    cached_candidates = []

    def write_report(force: bool = False) -> None:
        nonlocal last_report_write
        now = time.time()
        if not force and now - last_report_write < 30.0:
            return
        open_cost = sum(p.position_value_usd for p in positions.values())
        report = {
            "strategy": "pump_fun_pre_graduation_to_dex",
            "mode": "PAPER_ONLY",
            "duration_minutes": args.duration_minutes,
            "started_at": started,
            "updated_at": now,
            "finished_at": now if now >= deadline else None,
            "wallet": {
                "initial_cash_usd": INITIAL_CASH_USD,
                "cash_usd": round(cash, 6),
                "open_positions": len(positions),
                "open_cost_basis_usd": round(open_cost, 6),
                "realized_pnl_usd": round(cash - INITIAL_CASH_USD + open_cost, 6),
                "paper_equity_cost_basis_usd": round(cash + open_cost, 6),
            },
            "scan_stats": {
                "scans": scans,
                "discovered_unique_mints": len(discovered_mints),
                "active_pregraduation_candidates_seen": len(candidate_events),
                "entries": len(positions) + len(completed),
                "graduations_seen": graduations_seen,
                "dex_quotes_seen": dex_quotes_seen,
                "api_errors": api_errors,
                "last_api_error": strategy.last_api_error(),
            },
            "paper_trades": [asdict(p) for p in completed] + [asdict(p) for p in positions.values()],
            "max_multiple": max_multiple,
            "candidate_events": candidate_events[-2000:],
            "live_money_execution": False,
            "notes": [
                "Entry is before Pump.fun graduation.",
                "Exit is counted only after completion and the first real Solana DEX quote.",
                "Ungraduated positions are not forcibly sold at the end of the window.",
                "No synthetic, guessed, or fallback DEX price is used.",
            ],
        }
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
        tmp = args.output + ".tmp"
        with open(tmp, "w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2, ensure_ascii=False)
        os.replace(tmp, args.output)
        last_report_write = now

    while time.time() < deadline:
        now = time.time()
        if now >= next_discovery:
            scans += 1
            try:
                cached_candidates = strategy.discover(limit=50, probe_limit=15)
            except Exception as exc:
                cached_candidates = []
                api_errors += 1
                print(f"DISCOVERY_ERROR {type(exc).__name__}: {exc}", flush=True)
            next_discovery = now + DISCOVERY_SECONDS

            for candidate in cached_candidates[:10]:
                discovered_mints.add(candidate.mint)
                candidate_events.append({
                    "observed_at": candidate.observed_at,
                    "mint": candidate.mint,
                    "symbol": candidate.symbol,
                    "score": candidate.total_score,
                    "integrity": candidate.integrity_score,
                    "activity": candidate.activity_score,
                    "curve_progress_pct": candidate.curve_progress_pct,
                    "buy_share_pct": candidate.buy_share_pct,
                    "buy_trades": candidate.buy_trades,
                    "sell_trades": candidate.sell_trades,
                    "unique_buyers": candidate.unique_buyers,
                    "price_usd": candidate.price_usd,
                })
            candidate_events[:] = candidate_events[-2000:]

            for candidate in cached_candidates[:5]:
                if len(positions) >= MAX_OPEN_POSITIONS:
                    break
                if candidate.mint in positions or any(p.mint == candidate.mint for p in completed):
                    continue
                if candidate.total_score < ENTRY_SCORE_THRESHOLD:
                    continue
                total_flow = candidate.buy_trades + candidate.sell_trades
                if total_flow > 0 and candidate.buy_trades < MIN_BUY_TRADES_WHEN_AVAILABLE:
                    continue
                if candidate.buy_share_pct is not None and candidate.buy_share_pct < 50.0:
                    continue
                if candidate.price_usd is None or candidate.price_usd <= 0:
                    continue
                position_value = min(MAX_POSITION_USD, cash * 0.20)
                if position_value < 5.0:
                    break
                paper = PaperGraduationTrade(
                    mint=candidate.mint,
                    symbol=candidate.symbol,
                    entry_price_usd=candidate.price_usd,
                    entry_time=now,
                    position_value_usd=round(position_value, 6),
                    quantity=position_value / candidate.price_usd,
                    entry_score=candidate.total_score,
                    curve_progress_pct=candidate.curve_progress_pct,
                )
                positions[candidate.mint] = paper
                cash -= position_value
                print(
                    f"PAPER_ENTRY {paper.symbol} score={paper.entry_score:.1f} "
                    f"curve={paper.curve_progress_pct if paper.curve_progress_pct is not None else 'NA'} "
                    f"price=${paper.entry_price_usd:.10f} size=${paper.position_value_usd:.2f}",
                    flush=True,
                )

        for mint, paper in list(positions.items()):
            coin = strategy.coin(mint, cache_seconds=0.0)
            if not coin or not bool(coin.get("complete")):
                continue
            if paper.graduation_time is None:
                paper.graduation_time = now
                graduations_seen += 1
                print(f"GRADUATION {paper.symbol} mint={mint}", flush=True)

            quote = strategy.first_dex_quote(mint)
            if not quote:
                paper.status = "PAPER_GRADUATED_WAITING_FOR_DEX"
                if now - (paper.graduation_time or now) > DEX_RETRY_SECONDS:
                    paper.status = "GRADUATED_NO_DEX_QUOTE"
                continue

            exit_price = float(quote["price"])
            multiple = exit_price / paper.entry_price_usd
            exit_value = paper.quantity * exit_price
            cash += exit_value
            paper.status = "GRADUATED_EXIT"
            paper.exit_time = now
            paper.exit_price_usd = exit_price
            paper.multiple = round(multiple, 8)
            paper.roi_pct = round((multiple - 1.0) * 100.0, 4)
            paper.exit_reason = "PUMP_FUN_GRADUATION_AND_FIRST_DEX_QUOTE"
            paper.dex = quote.get("dex")
            paper.dex_pair = quote.get("pair")
            dex_quotes_seen += 1
            max_multiple = max(max_multiple or multiple, multiple)
            completed.append(paper)
            del positions[mint]
            print(
                f"PAPER_EXIT {paper.symbol} multiple={multiple:.6f} roi={paper.roi_pct:.2f}% "
                f"dex={paper.dex or 'UNKNOWN'}", flush=True,
            )

        if now - last_log >= 30.0:
            top = cached_candidates[0] if cached_candidates else None
            if top:
                print(
                    f"PUMP_SCAN scans={scans} candidates={len(cached_candidates)} "
                    f"top={top.symbol}:{top.total_score:.1f} curve={top.curve_progress_pct} "
                    f"open={len(positions)} cash={cash:.2f}", flush=True,
                )
            else:
                print(f"PUMP_SCAN scans={scans} candidates=0 open={len(positions)} cash={cash:.2f}", flush=True)
            last_log = now
        write_report()
        time.sleep(max(0.5, min(args.poll_seconds, 3.0)))

    write_report(force=True)
    print(json.dumps({
        "strategy": "pump_fun_pre_graduation_to_dex",
        "mode": "PAPER_ONLY",
        "duration_minutes": args.duration_minutes,
        "entries": len(completed) + len(positions),
        "exits": len(completed),
        "open_positions": len(positions),
        "max_multiple": max_multiple,
        "cash_usd": round(cash, 6),
        "discovered_unique_mints": len(discovered_mints),
        "graduations_seen": graduations_seen,
        "dex_quotes_seen": dex_quotes_seen,
        "scans": scans,
        "api_errors": api_errors,
        "live_money_execution": False,
    }, indent=2, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
