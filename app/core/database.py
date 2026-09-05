"""
Database management layer for Meme Alpha Hunter.
Uses SQLite for zero-dependency, atomic, and reliable data persistence.
"""

import json
import os
import sqlite3
from typing import Any, Dict, List, Optional


class DatabaseManager:
    def __init__(self, db_path: str = "data/meme_hunter.db"):
        self.db_path = db_path
        self._is_memory = (db_path == ":memory:")
        self._shared_conn: Optional[sqlite3.Connection] = None

        if not self._is_memory:
            os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)

        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        if self._is_memory:
            if self._shared_conn is None:
                self._shared_conn = sqlite3.connect(":memory:", timeout=30.0, check_same_thread=False)
                self._shared_conn.row_factory = sqlite3.Row
            return self._shared_conn
        else:
            conn = sqlite3.connect(self.db_path, timeout=30.0, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            return conn

    def _init_db(self):
        conn = self._get_connection()
        cursor = conn.cursor()

        # Tokens table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS tokens (
            mint TEXT PRIMARY KEY,
            symbol TEXT,
            name TEXT,
            decimals INTEGER,
            liquidity REAL,
            market_cap REAL,
            price REAL,
            volume_24h REAL,
            buyers_24h INTEGER,
            sellers_24h INTEGER,
            holders_count INTEGER,
            creator TEXT,
            pool_address TEXT,
            chain TEXT DEFAULT 'solana',
            source TEXT,
            first_seen_ts REAL,
            updated_at REAL
        )
        """)

        # Token DNA snapshots
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS token_dna (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mint TEXT,
            timestamp REAL,
            price REAL,
            volume REAL,
            liquidity REAL,
            holders INTEGER,
            smart_money_flow REAL,
            whale_netflow REAL,
            regime TEXT,
            FOREIGN KEY (mint) REFERENCES tokens (mint)
        )
        """)

        # Wallets table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS wallets (
            address TEXT PRIMARY KEY,
            classification TEXT,
            confidence REAL,
            total_trades INTEGER,
            win_rate REAL,
            avg_roi REAL,
            cluster_id TEXT,
            updated_at REAL
        )
        """)

        # Whale events table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS whale_events (
            event_id TEXT PRIMARY KEY,
            wallet TEXT,
            mint TEXT,
            action TEXT,
            amount_usd REAL,
            token_amount REAL,
            price REAL,
            impact_score REAL,
            timestamp REAL
        )
        """)

        # Security reports table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS security_reports (
            mint TEXT PRIMARY KEY,
            security_score REAL,
            rug_probability REAL,
            mint_auth_revoked INTEGER,
            freeze_auth_revoked INTEGER,
            lp_locked_pct REAL,
            top10_holder_pct REAL,
            dev_holding_pct REAL,
            rejection_reasons TEXT,
            status TEXT,
            evaluated_at REAL
        )
        """)

        # Opportunity scores table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS opportunity_scores (
            mint TEXT PRIMARY KEY,
            symbol TEXT,
            alpha_score REAL,
            risk_score REAL,
            confidence_score REAL,
            earlyness_score REAL,
            execution_score REAL,
            final_score REAL,
            regime TEXT,
            narrative TEXT,
            recommendation TEXT,
            explanation_json TEXT,
            updated_at REAL
        )
        """)

        # Paper positions table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS paper_positions (
            position_id TEXT PRIMARY KEY,
            strategy_name TEXT,
            mint TEXT,
            symbol TEXT,
            entry_time REAL,
            entry_price REAL,
            size_usd REAL,
            tokens_amount REAL,
            current_price REAL,
            current_value REAL,
            unrealized_pnl REAL,
            unrealized_pnl_pct REAL,
            peak_price REAL,
            lowest_price REAL,
            status TEXT,
            updated_at REAL
        )
        """)

        # Paper trades journal table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS paper_trades (
            trade_id TEXT PRIMARY KEY,
            strategy_name TEXT,
            mint TEXT,
            symbol TEXT,
            entry_time REAL,
            entry_price REAL,
            size_usd REAL,
            simulated_fill_qty REAL,
            liquidity_usd REAL,
            slippage_usd REAL,
            fee_usd REAL,
            exit_time REAL,
            exit_price REAL,
            exit_reason TEXT,
            realized_pnl REAL,
            realized_pnl_pct REAL,
            mae_pct REAL,
            mfe_pct REAL,
            duration_sec REAL,
            alpha_score REAL,
            risk_score REAL,
            regime TEXT
        )
        """)

        # Portfolio ledger history
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS portfolio_ledger (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL,
            strategy_name TEXT,
            cash_balance REAL,
            equity REAL,
            open_positions_val REAL,
            realized_pnl REAL,
            unrealized_pnl REAL,
            total_fees REAL,
            total_slippage REAL,
            drawdown_pct REAL
        )
        """)

        # Health monitor table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS system_health (
            component TEXT PRIMARY KEY,
            status TEXT,
            message TEXT,
            updated_at REAL
        )
        """)

        conn.commit()
        if not self._is_memory:
            conn.close()

    # --- CRUD operations ---

    def upsert_token(self, token_data: Dict[str, Any]):
        conn = self._get_connection()
        try:
            conn.execute("""
            INSERT INTO tokens (
                mint, symbol, name, decimals, liquidity, market_cap, price,
                volume_24h, buyers_24h, sellers_24h, holders_count, creator,
                pool_address, chain, source, first_seen_ts, updated_at
            ) VALUES (
                :mint, :symbol, :name, :decimals, :liquidity, :market_cap, :price,
                :volume_24h, :buyers_24h, :sellers_24h, :holders_count, :creator,
                :pool_address, :chain, :source, :first_seen_ts, :updated_at
            )
            ON CONFLICT(mint) DO UPDATE SET
                symbol=excluded.symbol,
                name=excluded.name,
                decimals=excluded.decimals,
                liquidity=excluded.liquidity,
                market_cap=excluded.market_cap,
                price=excluded.price,
                volume_24h=excluded.volume_24h,
                buyers_24h=excluded.buyers_24h,
                sellers_24h=excluded.sellers_24h,
                holders_count=excluded.holders_count,
                updated_at=excluded.updated_at
            """, token_data)
            conn.commit()
        finally:
            if not self._is_memory:
                conn.close()

    def record_dna_snapshot(self, snapshot: Dict[str, Any]):
        conn = self._get_connection()
        try:
            conn.execute("""
            INSERT INTO token_dna (
                mint, timestamp, price, volume, liquidity, holders,
                smart_money_flow, whale_netflow, regime
            ) VALUES (
                :mint, :timestamp, :price, :volume, :liquidity, :holders,
                :smart_money_flow, :whale_netflow, :regime
            )
            """, snapshot)
            conn.commit()
        finally:
            if not self._is_memory:
                conn.close()

    def get_token_dna(self, mint: str, limit: int = 50) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        try:
            rows = conn.execute("""
            SELECT * FROM token_dna WHERE mint = ? ORDER BY timestamp ASC LIMIT ?
            """, (mint, limit)).fetchall()
            return [dict(r) for r in rows]
        finally:
            if not self._is_memory:
                conn.close()

    def upsert_security_report(self, report: Dict[str, Any]):
        conn = self._get_connection()
        try:
            conn.execute("""
            INSERT INTO security_reports (
                mint, security_score, rug_probability, mint_auth_revoked,
                freeze_auth_revoked, lp_locked_pct, top10_holder_pct,
                dev_holding_pct, rejection_reasons, status, evaluated_at
            ) VALUES (
                :mint, :security_score, :rug_probability, :mint_auth_revoked,
                :freeze_auth_revoked, :lp_locked_pct, :top10_holder_pct,
                :dev_holding_pct, :rejection_reasons, :status, :evaluated_at
            )
            ON CONFLICT(mint) DO UPDATE SET
                security_score=excluded.security_score,
                rug_probability=excluded.rug_probability,
                mint_auth_revoked=excluded.mint_auth_revoked,
                freeze_auth_revoked=excluded.freeze_auth_revoked,
                lp_locked_pct=excluded.lp_locked_pct,
                top10_holder_pct=excluded.top10_holder_pct,
                dev_holding_pct=excluded.dev_holding_pct,
                rejection_reasons=excluded.rejection_reasons,
                status=excluded.status,
                evaluated_at=excluded.evaluated_at
            """, report)
            conn.commit()
        finally:
            if not self._is_memory:
                conn.close()

    def upsert_opportunity_score(self, score_data: Dict[str, Any]):
        conn = self._get_connection()
        try:
            conn.execute("""
            INSERT INTO opportunity_scores (
                mint, symbol, alpha_score, risk_score, confidence_score,
                earlyness_score, execution_score, final_score, regime,
                narrative, recommendation, explanation_json, updated_at
            ) VALUES (
                :mint, :symbol, :alpha_score, :risk_score, :confidence_score,
                :earlyness_score, :execution_score, :final_score, :regime,
                :narrative, :recommendation, :explanation_json, :updated_at
            )
            ON CONFLICT(mint) DO UPDATE SET
                symbol=excluded.symbol,
                alpha_score=excluded.alpha_score,
                risk_score=excluded.risk_score,
                confidence_score=excluded.confidence_score,
                earlyness_score=excluded.earlyness_score,
                execution_score=excluded.execution_score,
                final_score=excluded.final_score,
                regime=excluded.regime,
                narrative=excluded.narrative,
                recommendation=excluded.recommendation,
                explanation_json=excluded.explanation_json,
                updated_at=excluded.updated_at
            """, score_data)
            conn.commit()
        finally:
            if not self._is_memory:
                conn.close()

    def record_whale_event(self, event: Dict[str, Any]):
        conn = self._get_connection()
        try:
            conn.execute("""
            INSERT OR REPLACE INTO whale_events (
                event_id, wallet, mint, action, amount_usd,
                token_amount, price, impact_score, timestamp
            ) VALUES (
                :event_id, :wallet, :mint, :action, :amount_usd,
                :token_amount, :price, :impact_score, :timestamp
            )
            """, event)
            conn.commit()
        finally:
            if not self._is_memory:
                conn.close()

    def save_trade(self, trade: Dict[str, Any]):
        conn = self._get_connection()
        try:
            conn.execute("""
            INSERT OR REPLACE INTO paper_trades (
                trade_id, strategy_name, mint, symbol, entry_time,
                entry_price, size_usd, simulated_fill_qty, liquidity_usd,
                slippage_usd, fee_usd, exit_time, exit_price, exit_reason,
                realized_pnl, realized_pnl_pct, mae_pct, mfe_pct,
                duration_sec, alpha_score, risk_score, regime
            ) VALUES (
                :trade_id, :strategy_name, :mint, :symbol, :entry_time,
                :entry_price, :size_usd, :simulated_fill_qty, :liquidity_usd,
                :slippage_usd, :fee_usd, :exit_time, :exit_price, :exit_reason,
                :realized_pnl, :realized_pnl_pct, :mae_pct, :mfe_pct,
                :duration_sec, :alpha_score, :risk_score, :regime
            )
            """, trade)
            conn.commit()
        finally:
            if not self._is_memory:
                conn.close()

    def record_portfolio_snapshot(self, snapshot: Dict[str, Any]):
        conn = self._get_connection()
        try:
            conn.execute("""
            INSERT INTO portfolio_ledger (
                timestamp, strategy_name, cash_balance, equity,
                open_positions_val, realized_pnl, unrealized_pnl,
                total_fees, total_slippage, drawdown_pct
            ) VALUES (
                :timestamp, :strategy_name, :cash_balance, :equity,
                :open_positions_val, :realized_pnl, :unrealized_pnl,
                :total_fees, :total_slippage, :drawdown_pct
            )
            """, snapshot)
            conn.commit()
        finally:
            if not self._is_memory:
                conn.close()

    def update_health(self, component: str, status: str, message: str, updated_at: float):
        conn = self._get_connection()
        try:
            conn.execute("""
            INSERT INTO system_health (component, status, message, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(component) DO UPDATE SET
                status=excluded.status,
                message=excluded.message,
                updated_at=excluded.updated_at
            """, (component, status, message, updated_at))
            conn.commit()
        finally:
            if not self._is_memory:
                conn.close()

    def get_all_tokens(self) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        try:
            rows = conn.execute("SELECT * FROM tokens ORDER BY updated_at DESC").fetchall()
            return [dict(r) for r in rows]
        finally:
            if not self._is_memory:
                conn.close()

    def get_all_trades(self, strategy_name: Optional[str] = None) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        try:
            if strategy_name:
                rows = conn.execute("SELECT * FROM paper_trades WHERE strategy_name = ? ORDER BY exit_time ASC", (strategy_name,)).fetchall()
            else:
                rows = conn.execute("SELECT * FROM paper_trades ORDER BY exit_time ASC").fetchall()
            return [dict(r) for r in rows]
        finally:
            if not self._is_memory:
                conn.close()

    def get_top_opportunities(self, limit: int = 10) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        try:
            rows = conn.execute("""
            SELECT * FROM opportunity_scores ORDER BY final_score DESC LIMIT ?
            """, (limit,)).fetchall()
            return [dict(r) for r in rows]
        finally:
            if not self._is_memory:
                conn.close()

    def get_whale_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        try:
            rows = conn.execute("SELECT * FROM whale_events ORDER BY timestamp DESC LIMIT ?", (limit,)).fetchall()
            return [dict(r) for r in rows]
        finally:
            if not self._is_memory:
                conn.close()

    def fetch_all(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        try:
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]
        finally:
            if not self._is_memory:
                conn.close()

    def get_security_reports(self) -> List[Dict[str, Any]]:
        conn = self._get_connection()
        try:
            rows = conn.execute("SELECT * FROM security_reports ORDER BY evaluated_at DESC").fetchall()
            return [dict(r) for r in rows]
        finally:
            if not self._is_memory:
                conn.close()
