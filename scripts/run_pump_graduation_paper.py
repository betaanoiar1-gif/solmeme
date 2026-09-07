"""Run the Pump.fun -> DEX graduation strategy in paper mode.

The experiment uses public Pump.fun HTTP data and the existing public DEX reader.
It never signs or submits a transaction.
"""

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List

# Allow direct execution as `python3 scripts/...py` from repository root.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from data.ingestion.dex_provider import DexPublicProvider
from strategies.pump_graduation_strategy import PumpGraduationStrategy


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration-minutes", type=float, default=5.0)
    parser.add_argument("--candidates", type=int, default=3)
    parser.add_argument("--poll-seconds", type=float, default=3.0)
    parser.add_argument("--output", default="reports/pump_graduation_strategy.json")
    args = parser.parse_args()

    strategy = PumpGraduationStrategy()
    dex = DexPublicProvider()
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)

    ranked = strategy.rank(limit=max(5, args.candidates * 2))
    candidates = ranked[: args.candidates]
    started = time.time()

    paper_trades: List[Dict[str, Any]] = []
    for c in candidates:
        if c.price_usd is None or c.price_usd <= 0:
            continue
        paper_trades.append({
            "mint": c.mint,
            "symbol": c.symbol,
            "name": c.name,
            "score": c.total_score,
            "integrity_score": c.integrity_score,
            "activity_score": c.activity_score,
            "graduation_score": c.graduation_score,
            "age_minutes": c.age_minutes,
            "curve_progress_pct": c.curve_progress_pct,
            "entry_price_usd": c.price_usd,
            "entry_time": time.time(),
            "status": "PAPER_HOLDING",
            "exit_price_usd": None,
            "roi_pct": None,
            "multiple": None,
            "exit_reason": None,
        })

    def monitor(i: int, trade: Dict[str, Any]) -> Dict[str, Any]:
        remaining = max(0.0, args.duration_minutes * 60.0 - (time.time() - started))
        graduated = strategy.wait_for_graduation(
            trade["mint"], timeout_seconds=remaining, interval_seconds=args.poll_seconds
        ) if remaining > 0 else None
        if graduated:
            state = dex.get_token_market_data(trade["mint"])
            exit_price = None
            if state:
                try:
                    exit_price = float(state["price"])
                except (TypeError, ValueError):
                    exit_price = None
            trade["status"] = "GRADUATED_EXIT" if exit_price else "GRADUATED_NO_DEX_QUOTE"
            trade["exit_time"] = time.time()
            trade["graduation_complete"] = True
            trade["pump_swap_pool"] = graduated.get("pump_swap_pool")
            trade["raydium_pool"] = graduated.get("raydium_pool")
            if exit_price and trade["entry_price_usd"]:
                trade["exit_price_usd"] = exit_price
                trade["multiple"] = round(exit_price / trade["entry_price_usd"], 6)
                trade["roi_pct"] = round((trade["multiple"] - 1.0) * 100.0, 2)
                trade["exit_reason"] = "PUMP_FUN_GRADUATION_AND_DEX_VISIBLE"
            else:
                trade["exit_reason"] = "PUMP_FUN_GRADUATION"
        else:
            trade["status"] = "NO_GRADUATION_WITHIN_TEST_WINDOW"
            trade["exit_time"] = time.time()
        return trade

    with ThreadPoolExecutor(max_workers=len(paper_trades) or 1) as pool:
        futures = [pool.submit(monitor, i, trade) for i, trade in enumerate(paper_trades)]
        for future in as_completed(futures):
            future.result()

    report = {
        "strategy": "pump_fun_pre_graduation_to_dex",
        "mode": "PAPER_ONLY",
        "duration_minutes": args.duration_minutes,
        "started_at": started,
        "finished_at": time.time(),
        "candidates": [c.__dict__ for c in candidates],
        "paper_trades": paper_trades,
        "graduated_trades": sum(1 for t in paper_trades if t.get("graduation_complete")),
        "dex_exits": sum(1 for t in paper_trades if t.get("status") == "GRADUATED_EXIT"),
        "max_multiple": max((t["multiple"] for t in paper_trades if t.get("multiple") is not None), default=None),
        "data_sources": ["Pump.fun public HTTP", "DexScreener public HTTP"],
        "live_money_execution": False,
    }
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
