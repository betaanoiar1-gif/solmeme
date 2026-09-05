import os
import shutil
import sqlite3
import sys
import tempfile
import time
import unittest

from blockchain.parsers.real_swap_parser import RealSwapRecord
from blockchain.solana.types import Provenance, SourceType
from intelligence.smart_money.emerging_smart_money import EmergingSmartMoneyEngine, EmergingWalletProfile
from intelligence.whales.relative_whale_engine import RelativeWhaleEngine, RelativeWhaleMetrics
from scoring.early_alpha.early_token_priority import (
    EarlyAlphaScoreResult,
    EarlyTokenPriorityFunnel,
    LiveTokenContext,
    execute_early_alpha_pipeline,
    load_live_context_from_canonical_db,
)


class TestEarlyAlphaEngine(unittest.TestCase):

    def setUp(self):
        self.es_engine = EmergingSmartMoneyEngine()
        self.funnel = EarlyTokenPriorityFunnel()
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_unknown_quote_remains_none(self):
        """A) UNKNOWN quote must remain None and never become 0.0 in smart money and whale engines."""
        swap_unverified = RealSwapRecord(
            signature="test_sig_unverified_quote",
            slot=1000,
            timestamp=time.time(),
            pool="Pool1",
            mint="Mint1",
            symbol="M1",
            wallet="wallet_no_quote",
            side="BUY",
            token_amount=500.0,
            quote_amount_sol=None,
            quote_amount_usd=None, # UNKNOWN quote
            price_usd=None,
            venue="Pump.fun",
            is_quote_verified=False
        )

        profile = self.es_engine.process_swap(swap_unverified, pool_liquidity_usd=50000.0)
        self.assertIsNone(profile.buy_volume_usd, "buy_volume_usd must remain None, never 0.0")
        self.assertIsNone(profile.sell_volume_usd, "sell_volume_usd must remain None, never 0.0")
        self.assertIsNone(profile.netflow_usd, "netflow_usd must remain None, never 0.0")
        self.assertIsNone(profile.avg_trade_size_usd, "avg_trade_size_usd must remain None, never 0.0")
        self.assertIsNone(profile.largest_trade_usd, "largest_trade_usd must remain None, never 0.0")
        self.assertEqual(profile.unverified_quote_swaps, 1)
        self.assertEqual(profile.verified_quote_swaps, 0)

        whale_metrics = RelativeWhaleEngine.evaluate_token("Mint1", "M1", [swap_unverified], pool_liquidity_usd=50000.0)
        self.assertIsNone(whale_metrics.absolute_netflow_usd, "absolute_netflow_usd must remain None")
        self.assertIsNone(whale_metrics.largest_single_buy_usd, "largest_single_buy_usd must remain None")
        self.assertIsNone(whale_metrics.flow_to_liquidity_ratio, "flow_to_liquidity_ratio must remain None")
        self.assertIsNone(whale_metrics.single_order_pool_impact_pct, "single_order_pool_impact_pct must remain None")

    def test_no_verified_whale_trades_underlying_metrics_remain_none(self):
        """B) When there are no verified whale trades, underlying USD metrics remain None."""
        small_swap = RealSwapRecord(
            signature="small_swap_1",
            slot=1000,
            timestamp=time.time(),
            pool="Pool1",
            mint="MintSmall",
            symbol="SMALL",
            wallet="wallet_small",
            side="BUY",
            token_amount=1000.0,
            quote_amount_sol=1.0,
            quote_amount_usd=100.0,  # Below WHALE_SWAP_MIN_USD ($2500)
            price_usd=0.10,
            venue="Pump.fun",
            is_whale=False,
            is_quote_verified=True
        )

        metrics = RelativeWhaleEngine.evaluate_token(
            mint="MintSmall",
            symbol="SMALL",
            swaps=[small_swap],
            pool_liquidity_usd=50000.0
        )

        self.assertIsNone(metrics.absolute_netflow_usd, "Underlying netflow must be None when no whale swaps exist")
        self.assertIsNone(metrics.largest_single_buy_usd, "Underlying largest buy must be None when no whale swaps exist")
        self.assertIsNone(metrics.whale_buy_acceleration, "Underlying acceleration must be None when no whale swaps exist")
        self.assertIsNone(metrics.flow_to_liquidity_ratio, "Flow to liquidity ratio must be None")
        self.assertIsNone(metrics.single_order_pool_impact_pct, "Single order pool impact must be None")
        self.assertEqual(metrics.accumulating_whales_count, 0)
        self.assertEqual(metrics.accumulation_events_count, 0)
        self.assertEqual(metrics.relative_whale_strength_score, 50.0)
        self.assertEqual(metrics.conviction_tier, "NEUTRAL")

    def test_stored_rpc_verified_0_stays_false(self):
        """C) Stored rpc_verified=0 in database remains False (never forced to True)."""
        db_path = os.path.join(self.temp_dir, "test_unverified.db")
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("""
        CREATE TABLE tokens (
            mint TEXT PRIMARY KEY, symbol TEXT, name TEXT, decimals INTEGER, supply REAL,
            price_usd REAL, liquidity_usd REAL, owner_program TEXT, mint_auth_revoked INTEGER,
            freeze_auth_revoked INTEGER, top10_holder_pct REAL, verification_status TEXT, source_type TEXT
        )""")
        c.execute("""
        CREATE TABLE live_swaps (
            signature TEXT PRIMARY KEY, slot INTEGER, block_time REAL, mint TEXT, wallet_pubkey TEXT,
            pool TEXT, venue TEXT, side TEXT, token_amount REAL, quote_sol REAL, quote_usd REAL,
            price_usd REAL, source_type TEXT, rpc_verified INTEGER, observed_at REAL
        )""")

        c.execute("INSERT INTO tokens VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                  ("MINT_UNVERIF", "UNV", "Unverified", 6, 1e9, 0.05, 50000.0, "TokenProg", 1, 1, 20.0, "UNVERIFIED", "REPLAY"))
        c.execute("INSERT INTO live_swaps VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                  ("sig_unverif_1", 100, 1700000000.0, "MINT_UNVERIF", "wallet_1", "pool_1", "Raydium", "BUY", 100.0, 1.0, 100.0, 1.0, "REPLAY", 0, 1700000001.0))
        conn.commit()
        conn.close()

        tokens, swaps = load_live_context_from_canonical_db(db_path)
        self.assertEqual(len(swaps), 1)
        self.assertFalse(swaps[0].provenance.verified_on_chain, "rpc_verified=0 must stay False")
        self.assertFalse(swaps[0].is_quote_verified, "is_quote_verified must be False when rpc_verified=0")
        self.assertFalse(tokens[0].is_mint_verified_on_chain, "Mint verification must remain False when UNVERIFIED")

    def test_stored_source_type_is_preserved(self):
        """D) Stored source_type in database is preserved (never overwritten to REAL)."""
        db_path = os.path.join(self.temp_dir, "test_source_type.db")
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("""
        CREATE TABLE tokens (
            mint TEXT PRIMARY KEY, symbol TEXT, name TEXT, decimals INTEGER, supply REAL,
            price_usd REAL, liquidity_usd REAL, owner_program TEXT, mint_auth_revoked INTEGER,
            freeze_auth_revoked INTEGER, top10_holder_pct REAL, verification_status TEXT, source_type TEXT
        )""")
        c.execute("""
        CREATE TABLE live_swaps (
            signature TEXT PRIMARY KEY, slot INTEGER, block_time REAL, mint TEXT, wallet_pubkey TEXT,
            pool TEXT, venue TEXT, side TEXT, token_amount REAL, quote_sol REAL, quote_usd REAL,
            price_usd REAL, source_type TEXT, rpc_verified INTEGER, observed_at REAL
        )""")

        c.execute("INSERT INTO tokens VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                  ("MINT_REPLAY", "REP", "ReplayToken", 6, 1e9, 0.05, 50000.0, "TokenProg", 1, 1, 20.0, "VERIFIED_ON_CHAIN", "REPLAY"))
        c.execute("INSERT INTO live_swaps VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                  ("sig_rep_1", 100, 1700000000.0, "MINT_REPLAY", "wallet_1", "pool_1", "Raydium", "BUY", 100.0, 1.0, 100.0, 1.0, "REPLAY", 1, 1700000001.0))
        conn.commit()
        conn.close()

        tokens, swaps = load_live_context_from_canonical_db(db_path)
        self.assertEqual(swaps[0].provenance.source_type, SourceType.REPLAY)
        self.assertEqual(tokens[0].source_type, SourceType.REPLAY)

    def test_pool_age_is_never_hardcoded(self):
        """E) Pool age is derived from verified swap timestamps without static constants."""
        db_path = os.path.join(self.temp_dir, "test_pool_age.db")
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("""
        CREATE TABLE tokens (
            mint TEXT PRIMARY KEY, symbol TEXT, name TEXT, decimals INTEGER, supply REAL,
            price_usd REAL, liquidity_usd REAL, owner_program TEXT, mint_auth_revoked INTEGER,
            freeze_auth_revoked INTEGER, top10_holder_pct REAL, verification_status TEXT, source_type TEXT
        )""")
        c.execute("""
        CREATE TABLE live_swaps (
            signature TEXT PRIMARY KEY, slot INTEGER, block_time REAL, mint TEXT, wallet_pubkey TEXT,
            pool TEXT, venue TEXT, side TEXT, token_amount REAL, quote_sol REAL, quote_usd REAL,
            price_usd REAL, source_type TEXT, rpc_verified INTEGER, observed_at REAL
        )""")

        c.execute("INSERT INTO tokens VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                  ("MINT_AGE", "AGE", "AgeToken", 6, 1e9, 0.05, 50000.0, "TokenProg", 1, 1, 20.0, "VERIFIED_ON_CHAIN", "REAL"))
        # Insert 2 swaps 30 minutes apart (1800 seconds)
        c.execute("INSERT INTO live_swaps VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                  ("sig_age_1", 100, 1700000000.0, "MINT_AGE", "wallet_1", "pool_1", "Raydium", "BUY", 100.0, 1.0, 100.0, 1.0, "REAL", 1, 1700000001.0))
        c.execute("INSERT INTO live_swaps VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                  ("sig_age_2", 110, 1700001800.0, "MINT_AGE", "wallet_2", "pool_1", "Raydium", "BUY", 100.0, 1.0, 100.0, 1.0, "REAL", 1, 1700001801.0))
        conn.commit()
        conn.close()

        tokens, swaps = load_live_context_from_canonical_db(db_path)
        self.assertEqual(tokens[0].pool_age_minutes, 30.0, "Pool age must be derived as exactly 30.0 minutes")

    def test_missing_pool_age_becomes_none(self):
        """F) Missing pool age becomes None and degrades confidence strictly."""
        ctx = LiveTokenContext(
            mint="MINT_NO_AGE",
            symbol="NO_AGE",
            pool_age_minutes=None, # Missing pool age
            pool_liquidity_usd=50000.0,
            price_usd=0.05,
            is_mint_verified_on_chain=True,
            is_market_data_verified=True,
            quote_quality=1.0
        )
        res = self.funnel.score_live_token(ctx, [])
        self.assertEqual(res.earlyness_score, 50.0, "Earlyness score must default to neutral 50.0 when age is unknown")
        self.assertLess(res.confidence, 1.0, "Confidence must degrade when pool age is missing")
        self.assertEqual(res.confidence, 0.90)

    def test_no_static_numeric_market_metadata_exists_in_production_path(self):
        """G) No static numeric token arrays exist in scoring module."""
        import scoring.early_alpha.early_token_priority as ep
        self.assertFalse(hasattr(ep, "ALL_42_VERIFIED_TOKENS"))
        self.assertFalse(hasattr(ep, "STATIC_TOKENS"))

    def test_no_forced_real_provenance_exists_in_db_loader(self):
        """H) No forced REAL provenance exists in DB loader when loading arbitrary source_type."""
        db_path = os.path.join(self.temp_dir, "test_mock_loader.db")
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("""
        CREATE TABLE tokens (
            mint TEXT PRIMARY KEY, symbol TEXT, name TEXT, decimals INTEGER, supply REAL,
            price_usd REAL, liquidity_usd REAL, owner_program TEXT, mint_auth_revoked INTEGER,
            freeze_auth_revoked INTEGER, top10_holder_pct REAL, verification_status TEXT, source_type TEXT
        )""")
        c.execute("""
        CREATE TABLE live_swaps (
            signature TEXT PRIMARY KEY, slot INTEGER, block_time REAL, mint TEXT, wallet_pubkey TEXT,
            pool TEXT, venue TEXT, side TEXT, token_amount REAL, quote_sol REAL, quote_usd REAL,
            price_usd REAL, source_type TEXT, rpc_verified INTEGER, observed_at REAL
        )""")

        c.execute("INSERT INTO tokens VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                  ("MINT_MOCK", "MCK", "MockToken", 6, 1e9, 0.05, 50000.0, "TokenProg", 1, 1, 20.0, "VERIFIED_ON_CHAIN", "SNAPSHOT"))
        c.execute("INSERT INTO live_swaps VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                  ("sig_mock_1", 100, 1700000000.0, "MINT_MOCK", "wallet_1", "pool_1", "Raydium", "BUY", 100.0, 1.0, 100.0, 1.0, "SNAPSHOT", 0, 1700000001.0))
        conn.commit()
        conn.close()

        tokens, swaps = load_live_context_from_canonical_db(db_path)
        self.assertEqual(swaps[0].provenance.source_type, SourceType.SNAPSHOT)
        self.assertEqual(tokens[0].source_type, SourceType.SNAPSHOT)
        self.assertFalse(swaps[0].provenance.verified_on_chain)


if __name__ == "__main__":
    unittest.main()
