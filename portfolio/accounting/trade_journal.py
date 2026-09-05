"""
Comprehensive Trade Journal.
Logs granular trade records including MAE, MFE, and multi-factor signals.
"""

from dataclasses import dataclass, asdict
import logging
import time
from typing import Any, Dict, List, Optional
import uuid

from app.core.database import DatabaseManager

logger = logging.getLogger("meme_alpha_hunter.journal")


@dataclass
class TradeRecord:
    trade_id: str
    strategy_name: str
    mint: str
    symbol: str
    entry_time: float
    entry_price: float
    size_usd: float
    simulated_fill_qty: float
    liquidity_usd: float
    slippage_usd: float
    fee_usd: float
    exit_time: float
    exit_price: float
    exit_reason: str
    realized_pnl: float
    realized_pnl_pct: float
    mae_pct: float  # Maximum Adverse Excursion
    mfe_pct: float  # Maximum Favorable Excursion
    duration_sec: float
    alpha_score: float
    risk_score: float
    regime: str


class TradeJournal:
    def __init__(self, db: Optional[DatabaseManager] = None):
        self.db = db or DatabaseManager()
        self.records: List[TradeRecord] = []

    def record_completed_trade(
        self,
        strategy_name: str,
        mint: str,
        symbol: str,
        entry_time: float,
        entry_price: float,
        size_usd: float,
        simulated_fill_qty: float,
        liquidity_usd: float,
        slippage_usd: float,
        fee_usd: float,
        exit_time: float,
        exit_price: float,
        exit_reason: str,
        realized_pnl: float,
        peak_price: float,
        lowest_price: float,
        alpha_score: float,
        risk_score: float,
        regime: str
    ) -> TradeRecord:
        pnl_pct = (realized_pnl / max(size_usd, 1e-9)) * 100.0
        duration = exit_time - entry_time

        # MAE & MFE computation
        mfe_pct = ((peak_price - entry_price) / max(entry_price, 1e-9)) * 100.0
        mae_pct = ((lowest_price - entry_price) / max(entry_price, 1e-9)) * 100.0

        record = TradeRecord(
            trade_id=str(uuid.uuid4())[:8],
            strategy_name=strategy_name,
            mint=mint,
            symbol=symbol,
            entry_time=entry_time,
            entry_price=entry_price,
            size_usd=size_usd,
            simulated_fill_qty=simulated_fill_qty,
            liquidity_usd=liquidity_usd,
            slippage_usd=slippage_usd,
            fee_usd=fee_usd,
            exit_time=exit_time,
            exit_price=exit_price,
            exit_reason=exit_reason,
            realized_pnl=round(realized_pnl, 4),
            realized_pnl_pct=round(pnl_pct, 2),
            mae_pct=round(mae_pct, 2),
            mfe_pct=round(mfe_pct, 2),
            duration_sec=round(duration, 2),
            alpha_score=round(alpha_score, 2),
            risk_score=round(risk_score, 2),
            regime=regime
        )

        self.records.append(record)

        try:
            self.db.save_trade(asdict(record))
        except Exception as e:
            logger.error(f"Failed to save trade record {record.trade_id}: {e}")

        return record

    def get_strategy_trades(self, strategy_name: str) -> List[TradeRecord]:
        return [r for r in self.records if r.strategy_name == strategy_name]
