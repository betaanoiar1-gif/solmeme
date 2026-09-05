import os
import shutil
import sqlite3
import sys
import tempfile
import time
import unittest

from blockchain.parsers.real_swap_parser import RealSwapRecord
from blockchain.solana.types import Provenance, SourceType
from intelligence.smart_money.emerging_smart_money import (
    EmergingSmartMoneyEngine,
    EmergingWalletProfile,
    is_swap_quote_verified as is_swap_quote_verified_sm,
)
from intelligence.whales.relative_whale_engine import (
    RelativeWhaleEngine,
    RelativeWhaleMetrics,
    is_swap_quote_verified as is_swap_quote_verified_rw,
)
from scoring.early_alpha.early_token_priority import (
    EarlyAlphaScoreResult,
    EarlyTokenPriorityFunnel,
    LiveTokenContext,
    execute_early_alpha_pipeline,
    is_swap_quote_verified,
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

    def test_numeric_quote_with_rpc_verified_0_is_not_verified(self):
        """Numeric quote + is_quote_verified=False or verified_on_chain=False => NOT verified."""
        swap_unverified = RealSwapRecord(
            signature="sig_unverified_numeric",
            slot=1000,
            timestamp=time.time(),
            pool="Pool1",
            mint="Mint1",
            symbol="M1",
            wallet="wallet_1",
            side="BUY",
            token_amount=500.0,
            quote_amount_sol=5.0,
            quote_amount_usd=500.0,  # Numeric quote present
            price_usd=1.0,
            venue="Pump.fun",
            is_quote_verified=False,  # NOT verified
            provenance=Provenance(source_type=SourceType.REAL, verified_on_chain=False)  # NOT verified on-chain
        )

        self.assertFalse(is_swap_quote_verified(swap_unverified))
        self.assertFalse(is_swap_quote_verified_sm(swap_unverified))
        self.assertFalse(is_swap_quote_verified_rw(swap_unverified))

        profile = self.es_engine.process_swap(swap_unverified, pool_liquidity_usd=50000.0)
        self.assertEqual(profile.unverified_quote_swaps, 1)
        self.assertEqual(profile.verified_quote_swaps, 0)
        self.assertIsNone(profile.buy_volume_usd, "Unverified numeric quote must not add to buy_volume_usd")
        self.assertIsNone(profile.netflow_usd, "Unverified numeric quote must not add to netflow_usd")

    def test_numeric_quote_with_rpc_verified_1_is_verified(self):
        """Numeric quote + is_quote_verified=True + verified_on_chain=True => Verified."""
        swap_verified = RealSwapRecord(
            signature="sig_verified_numeric",
            slot=1000,
            timestamp=time.time(),
            pool="Pool1",
            mint="Mint1",
            symbol="M1",
            wallet="wallet_2",
            side="BUY",
            token_amount=500.0,
            quote_amount_sol=5.0,
            quote_amount_usd=500.0,
            price_usd=1.0,
            venue="Pump.fun",
            is_quote_verified=True,
            provenance=Provenance(source_type=SourceType.REAL, verified_on_chain=True)
        )

        self.assertTrue(is_swap_quote_verified(swap_verified))
        profile = self.es_engine.process_swap(swap_verified, pool_liquidity_usd=50000.0)
        self.assertEqual(profile.verified_quote_swaps, 1)
        self.assertEqual(profile.unverified_quote_swaps, 0)
        self.assertEqual(profile.buy_volume_usd, 500.0)
        self.assertEqual(profile.netflow_usd, 500.0)

    def test_quote_quality_excludes_unverified_numeric_quotes(self):
        """quote_quality must strictly reflect verified_swaps / total_swaps."""
        s1 = RealSwapRecord(
            signature="s1_verified",
            slot=1000,
            timestamp=time.time(),
            pool="Pool1",
            mint="MintQ",
            symbol="Q",
            wallet="wallet_1",
            side="BUY",
            token_amount=100.0,
            quote_amount_sol=1.0,
            quote_amount_usd=100.0,
            price_usd=1.0,
            venue="Pump.fun",
            is_quote_verified=True,
            provenance=Provenance(source_type=SourceType.REAL, verified_on_chain=True)
        )
        s2 = RealSwapRecord(
            signature="s2_unverified_numeric",
            slot=1001,
            timestamp=time.time(),
            pool="Pool1",
            mint="MintQ",
            symbol="Q",
            wallet="wallet_2",
            side="BUY",
            token_amount=200.0,
            quote_amount_sol=2.0,
            quote_amount_usd=200.0,  # Unverified numeric quote
            price_usd=1.0,
            venue="Pump.fun",
            is_quote_verified=False,
            provenance=Provenance(source_type=SourceType.REAL, verified_on_chain=False)
        )

        engine = EmergingSmartMoneyEngine()
        engine.process_swap(s1)
        engine.process_swap(s2)
        signal = engine.evaluate_token_signal("MintQ", "Q")

        self.assertEqual(signal.quote_quality, 0.50, "Quote quality must be exactly 1/2 = 0.50")
        whale_metrics = RelativeWhaleEngine.evaluate_token("MintQ", "Q", [s1, s2], pool_liquidity_usd=50000.0)
        self.assertEqual(whale_metrics.quote_quality, 0.50)

    def test_unverified_numeric_quote_does_not_affect_buy_volume(self):
        """Unverified numeric quote ($10k) does not participate in buy volume."""
        s_unverified = RealSwapRecord(
            signature="s_fake_buy",
            slot=1000,
            timestamp=time.time(),
            pool="Pool1",
            mint="MintVol",
            symbol="VOL",
            wallet="wallet_fake",
            side="BUY",
            token_amount=10000.0,
            quote_amount_sol=100.0,
            quote_amount_usd=10000.0,
            price_usd=1.0,
            venue="Pump.fun",
            is_quote_verified=False,
            provenance=Provenance(source_type=SourceType.REAL, verified_on_chain=False)
        )
        profile = self.es_engine.process_swap(s_unverified, pool_liquidity_usd=50000.0)
        self.assertIsNone(profile.buy_volume_usd)

    def test_unverified_numeric_quote_does_not_affect_netflow(self):
        """Verified buy ($100) + unverified numeric sell ($5000) yields netflow = $100."""
        s_verified_buy = RealSwapRecord(
            signature="s_v_buy",
            slot=1000,
            timestamp=time.time(),
            pool="Pool1",
            mint="MintNet",
            symbol="NET",
            wallet="wallet_mix",
            side="BUY",
            token_amount=100.0,
            quote_amount_sol=1.0,
            quote_amount_usd=100.0,
            price_usd=1.0,
            venue="Pump.fun",
            is_quote_verified=True,
            provenance=Provenance(source_type=SourceType.REAL, verified_on_chain=True)
        )
        s_unverified_sell = RealSwapRecord(
            signature="s_unv_sell",
            slot=1001,
            timestamp=time.time(),
            pool="Pool1",
            mint="MintNet",
            symbol="NET",
            wallet="wallet_mix",
            side="SELL",
            token_amount=5000.0,
            quote_amount_sol=50.0,
            quote_amount_usd=5000.0,
            price_usd=1.0,
            venue="Pump.fun",
            is_quote_verified=False,
            provenance=Provenance(source_type=SourceType.REAL, verified_on_chain=False)
        )

        self.es_engine.process_swap(s_verified_buy)
        profile = self.es_engine.process_swap(s_unverified_sell)

        self.assertEqual(profile.buy_volume_usd, 100.0)
        self.assertIsNone(profile.sell_volume_usd)
        self.assertEqual(profile.netflow_usd, 100.0, "Netflow must remain strictly $100.0 from verified buy")

    def test_unverified_numeric_quote_does_not_affect_imbalance(self):
        """Microstructural imbalance ignores unverified numeric quotes."""
        s_v_buy = RealSwapRecord(
            signature="s_v_buy_imb",
            slot=1000,
            timestamp=time.time(),
            pool="Pool1",
            mint="MintImb",
            symbol="IMB",
            wallet="w1",
            side="BUY",
            token_amount=100.0,
            quote_amount_sol=1.0,
            quote_amount_usd=100.0,
            price_usd=1.0,
            venue="Pump.fun",
            is_quote_verified=True,
            provenance=Provenance(source_type=SourceType.REAL, verified_on_chain=True)
        )
        s_unv_sell = RealSwapRecord(
            signature="s_unv_sell_imb",
            slot=1001,
            timestamp=time.time(),
            pool="Pool1",
            mint="MintImb",
            symbol="IMB",
            wallet="w2",
            side="SELL",
            token_amount=100000.0,
            quote_amount_sol=1000.0,
            quote_amount_usd=100000.0, # Massive unverified quote
            price_usd=1.0,
            venue="Pump.fun",
            is_quote_verified=False,
            provenance=Provenance(source_type=SourceType.REAL, verified_on_chain=False)
        )

        ctx = LiveTokenContext(
            mint="MintImb",
            symbol="IMB",
            pool_liquidity_usd=50000.0,
            is_mint_verified_on_chain=True,
            is_market_data_verified=True
        )

        res = self.funnel.score_live_token(ctx, [s_v_buy, s_unv_sell])
        self.assertEqual(res.imbalance_momentum_score, 100.0, "Imbalance must be 100.0 (100% buy momentum among verified quotes)")

    def test_pool_age_is_based_on_pool_creation_timestamp(self):
        """Pool age must strictly represent: (current_observation_time - verified_pool_creation_time)."""
        now = time.time()
        pool_creation_ts = now - (3600.0) # Created exactly 60.0 minutes ago

        ctx = LiveTokenContext(
            mint="MintPoolAge",
            symbol="AGE",
            observed_at=now,
            pool_created_at=pool_creation_ts,
            pool_liquidity_usd=50000.0,
            is_mint_verified_on_chain=True,
            is_market_data_verified=True
        )

        res = self.funnel.score_live_token(ctx, [])
        self.assertEqual(res.pool_age_minutes, 60.0, "Pool age must be exactly 60.0 minutes")
        self.assertEqual(res.earlyness_score, 85.0)

    def test_swap_observation_window_cannot_be_used_as_pool_age(self):
        """Swap observation window (span of swap timestamps) cannot be used as pool age."""
        now = time.time()
        # 2 swaps spanning 120 minutes window
        s1 = RealSwapRecord(
            signature="s1_win",
            slot=1000,
            timestamp=now - 7200.0,
            pool="Pool1",
            mint="MintWin",
            symbol="WIN",
            wallet="w1",
            side="BUY",
            token_amount=10.0,
            quote_amount_sol=1.0,
            quote_amount_usd=100.0,
            price_usd=10.0,
            venue="Pump.fun",
            is_quote_verified=True,
            provenance=Provenance(source_type=SourceType.REAL, verified_on_chain=True)
        )
        s2 = RealSwapRecord(
            signature="s2_win",
            slot=1010,
            timestamp=now,
            pool="Pool1",
            mint="MintWin",
            symbol="WIN",
            wallet="w2",
            side="BUY",
            token_amount=10.0,
            quote_amount_sol=1.0,
            quote_amount_usd=100.0,
            price_usd=10.0,
            venue="Pump.fun",
            is_quote_verified=True,
            provenance=Provenance(source_type=SourceType.REAL, verified_on_chain=True)
        )

        # Token with NO verified pool creation timestamp
        ctx = LiveTokenContext(
            mint="MintWin",
            symbol="WIN",
            pool_created_at=None, # UNKNOWN pool creation timestamp
            observed_at=now,
            price_usd=1.0,
            pool_liquidity_usd=50000.0,
            is_mint_verified_on_chain=True,
            is_market_data_verified=True
        )

        res = self.funnel.score_live_token(ctx, [s1, s2])
        self.assertIsNone(res.pool_age_minutes, "Pool age MUST remain None when pool_created_at is None, even if swaps span 120 minutes")
        self.assertEqual(res.earlyness_score, 50.0)
        self.assertEqual(res.confidence, 0.90)

    def test_stored_rpc_verified_0_stays_false(self):
        """Stored rpc_verified=0 in DB stays False."""
        db_path = os.path.join(self.temp_dir, "test_unverif_db.db")
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("""
        CREATE TABLE tokens (
            mint TEXT PRIMARY KEY, symbol TEXT, name TEXT, decimals INTEGER, supply REAL,
            price_usd REAL, liquidity_usd REAL, owner_program TEXT, mint_auth_revoked INTEGER,
            freeze_auth_revoked INTEGER, top10_holder_pct REAL, verification_status TEXT, source_type TEXT,
            pool_created_at REAL
        )""")
        c.execute("""
        CREATE TABLE live_swaps (
            signature TEXT PRIMARY KEY, slot INTEGER, block_time REAL, mint TEXT, wallet_pubkey TEXT,
            pool TEXT, venue TEXT, side TEXT, token_amount REAL, quote_sol REAL, quote_usd REAL,
            price_usd REAL, source_type TEXT, rpc_verified INTEGER, observed_at REAL
        )""")

        c.execute("INSERT INTO tokens VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                  ("MINT_U", "U", "Unv", 6, 1e9, 0.05, 50000.0, "TokenProg", 1, 1, 20.0, "UNVERIFIED", "REPLAY", None))
        c.execute("INSERT INTO live_swaps VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                  ("sig_u", 100, 1700000000.0, "MINT_U", "w1", "p1", "Raydium", "BUY", 100.0, 1.0, 100.0, 1.0, "REPLAY", 0, 1700000001.0))
        conn.commit()
        conn.close()

        tokens, swaps = load_live_context_from_canonical_db(db_path)
        self.assertFalse(swaps[0].provenance.verified_on_chain)
        self.assertFalse(swaps[0].is_quote_verified)
        self.assertFalse(tokens[0].is_mint_verified_on_chain)

    def test_stored_source_type_is_preserved(self):
        """Stored source_type in DB is preserved."""
        db_path = os.path.join(self.temp_dir, "test_src_db.db")
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("""
        CREATE TABLE tokens (
            mint TEXT PRIMARY KEY, symbol TEXT, name TEXT, decimals INTEGER, supply REAL,
            price_usd REAL, liquidity_usd REAL, owner_program TEXT, mint_auth_revoked INTEGER,
            freeze_auth_revoked INTEGER, top10_holder_pct REAL, verification_status TEXT, source_type TEXT,
            pool_created_at REAL
        )""")
        c.execute("""
        CREATE TABLE live_swaps (
            signature TEXT PRIMARY KEY, slot INTEGER, block_time REAL, mint TEXT, wallet_pubkey TEXT,
            pool TEXT, venue TEXT, side TEXT, token_amount REAL, quote_sol REAL, quote_usd REAL,
            price_usd REAL, source_type TEXT, rpc_verified INTEGER, observed_at REAL
        )""")

        c.execute("INSERT INTO tokens VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                  ("MINT_SNAP", "SNP", "Snap", 6, 1e9, 0.05, 50000.0, "TokenProg", 1, 1, 20.0, "VERIFIED_ON_CHAIN", "SNAPSHOT", 1700000000.0))
        c.execute("INSERT INTO live_swaps VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                  ("sig_snap", 100, 1700000000.0, "MINT_SNAP", "w1", "p1", "Raydium", "BUY", 100.0, 1.0, 100.0, 1.0, "SNAPSHOT", 1, 1700000001.0))
        conn.commit()
        conn.close()

        tokens, swaps = load_live_context_from_canonical_db(db_path)
        self.assertEqual(swaps[0].provenance.source_type, SourceType.SNAPSHOT)
        self.assertEqual(tokens[0].source_type, SourceType.SNAPSHOT)


if __name__ == "__main__":
    unittest.main()
