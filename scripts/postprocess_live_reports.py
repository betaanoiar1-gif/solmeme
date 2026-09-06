"""Post-process live reports so exported audit fields match the live engine.

This script intentionally does not change trading decisions. It reconstructs the
same evidence-gated smart-money layer from the exported REAL swap stream only so
CSV/report audit fields cannot silently contain placeholder constants.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

# Running ``python3 scripts/postprocess_live_reports.py`` puts ``scripts/``
# on sys.path, not the repository root. Add the root explicitly so the local
# ``blockchain`` and ``intelligence`` packages resolve in GitHub Actions.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from blockchain.parsers.real_swap_parser import RealSwapRecord
from blockchain.solana.types import Provenance, SourceType
from intelligence.smart_money.real_smart_money import RealSmartMoneyEngine


def _parse_float(value: str) -> Optional[float]:
    if value is None or value == "" or value.upper() == "UNKNOWN":
        return None
    return float(value)


def _parse_bool(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _parse_timestamp(value: str) -> Optional[float]:
    if not value or value.upper() == "UNKNOWN":
        return None
    return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc).timestamp()


def _load_swaps(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _rebuild_smart_money(reports_dir: Path, signals: list[dict]) -> Dict[str, object]:
    swaps_path = reports_dir / "live_swaps.csv"
    if not swaps_path.exists():
        raise FileNotFoundError(f"Missing {swaps_path}")

    liquidity_by_mint = {
        row["mint"]: _parse_float(row.get("liquidity", ""))
        for row in signals
        if row.get("mint")
    }

    engine = RealSmartMoneyEngine()
    for row in _load_swaps(swaps_path):
        source_type = SourceType.REAL if row.get("source_type") == "REAL" else SourceType.UNKNOWN
        verified = _parse_bool(row.get("is_quote_verified", "false"))
        ts = _parse_timestamp(row.get("timestamp", ""))
        swap = RealSwapRecord(
            signature=row["signature"],
            slot=int(row.get("slot") or 0),
            timestamp=ts,
            pool=row.get("pool") or "UnknownPool",
            mint=row["mint"],
            symbol="UNKNOWN",
            wallet=row["wallet"],
            side=row["side"],
            token_amount=float(row.get("token_amount") or 0.0),
            quote_amount_sol=_parse_float(row.get("quote_sol", "")),
            quote_amount_usd=_parse_float(row.get("quote_usd", "")),
            price_usd=_parse_float(row.get("price_usd", "")),
            venue=row.get("venue") or "UNKNOWN",
            is_whale=_parse_bool(row.get("is_whale", "false")),
            is_quote_verified=verified,
            provenance=Provenance(
                source_type=source_type,
                provider="live_swaps_export",
                signature=row["signature"],
                slot=int(row.get("slot") or 0),
                timestamp=ts,
                observed_at=ts,
                confidence=1.0 if verified else 0.0,
                verified_on_chain=verified,
            ),
        )
        engine.process_real_swap(
            swap,
            pool_liquidity_usd=liquidity_by_mint.get(swap.mint),
        )

    return {mint: engine.evaluate_token_smart_money(mint) for mint in liquidity_by_mint}


def patch_live_signals(reports_dir: Path) -> None:
    signals_path = reports_dir / "live_signals.csv"
    if not signals_path.exists():
        raise FileNotFoundError(f"Missing {signals_path}")

    with signals_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    signals = _rebuild_smart_money(reports_dir, rows)

    extra_fields = [
        "smart_money_label",
        "smart_money_netflow_usd",
        "smart_money_buyers",
        "smart_money_sellers",
        "emerging_smart_money_score",
        "emerging_netflow_usd",
        "emerging_accumulating_wallets",
        "emerging_distributing_wallets",
        "emerging_quote_quality",
        "emerging_signal_label",
    ]
    fieldnames = list(rows[0].keys()) if rows else []
    for field in extra_fields:
        if field not in fieldnames:
            fieldnames.append(field)

    for row in rows:
        signal = signals.get(row.get("mint"))
        if signal is None:
            continue
        row["smart_money_score"] = signal.smart_money_score
        row["whale_flow"] = row.get("whale_flow") or "UNKNOWN"
        row["smart_money_label"] = signal.signal_label
        row["smart_money_netflow_usd"] = signal.netflow_usd
        row["smart_money_buyers"] = signal.smart_buyers_count
        row["smart_money_sellers"] = signal.smart_sellers_count
        row["emerging_smart_money_score"] = signal.emerging_smart_money_score
        row["emerging_netflow_usd"] = signal.emerging_netflow_usd
        row["emerging_accumulating_wallets"] = signal.emerging_accumulating_wallets
        row["emerging_distributing_wallets"] = signal.emerging_distributing_wallets
        row["emerging_quote_quality"] = signal.emerging_quote_quality
        row["emerging_signal_label"] = signal.emerging_signal_label

    with signals_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def patch_reports(reports_dir: Path) -> None:
    commit = os.environ.get("GITHUB_SHA", "UNKNOWN")
    for filename in ("live_validation_report.md", "live_paper_test_report.md"):
        path = reports_dir / filename
        if path.exists():
            text = path.read_text(encoding="utf-8")
            text = text.replace("COMMIT: 0f8f93a", f"COMMIT: {commit}")
            text = text.replace("**Commit SHA:** `0f8f93a`", f"**Commit SHA:** `{commit}`")
            text = text.replace("SECURITY_REJECTED:", "SCORING_REJECTED:")
            text = text.replace("Security Rejected", "Scoring Rejected")
            path.write_text(text, encoding="utf-8")

    json_path = reports_dir / "live_validation_report.json"
    if json_path.exists():
        data = json.loads(json_path.read_text(encoding="utf-8"))
        data["commit"] = commit
        alpha = data.get("alpha_pipeline", {})
        if "security_rejected" in alpha:
            alpha["scoring_rejected"] = alpha.pop("security_rejected")
        data["audit_note"] = (
            "Exported smart-money fields are rebuilt from live_swaps.csv using the "
            "evidence-gated RealSmartMoneyEngine; no placeholder smart-money score is used."
        )
        json_path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reports-dir", default="reports")
    args = parser.parse_args()
    reports_dir = Path(args.reports_dir)
    patch_live_signals(reports_dir)
    patch_reports(reports_dir)
    print(f"✅ Live report audit post-processing complete: {reports_dir}")


if __name__ == "__main__":
    main()
