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
from scripts.build_canonical_provenance import (
    CanonicalProvenanceGuard,
    build_canonical_provenance,
)
from tests.fixtures.synthetic_fixture_builder import create_test_fixture_db


class TestEarlyAlphaEngine(unittest.TestCase):

    def setUp(self):
        self.es_engine = EmergingSmartMoneyEngine()
        self.funnel = EarlyTokenPriorityFunnel()
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    # =========================================================================
    # 1. Strict Quote Semantics & Pool Age Tests
    # =========================================================================

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
            quote_amount_usd=500.0,
            price_usd=1.0,
            venue="Pump.fun",
            is_quote_verified=False,
            provenance=Provenance(source_type=SourceType.REAL, verified_on_chain=False)
        )

        self.assertFalse(is_swap_quote_verified(swap_unverified))
        self.assertFalse(is_swap_quote_verified_sm(swap_unverified))
        self.assertFalse(is_swap_quote_verified_rw(swap_unverified))

        profile = self.es_engine.process_swap(swap_unverified, pool_liquidity_usd=50000.0)
        self.assertEqual(profile.unverified_quote_swaps, 1)
        self.assertEqual(profile.verified_quote_swaps, 0)
        self.assertIsNone(profile.buy_volume_usd)
        self.assertIsNone(profile.netflow_usd)

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
            quote_amount_usd=200.0,
            price_usd=1.0,
            venue="Pump.fun",
            is_quote_verified=False,
            provenance=Provenance(source_type=SourceType.REAL, verified_on_chain=False)
        )

        engine = EmergingSmartMoneyEngine()
        engine.process_swap(s1)
        engine.process_swap(s2)
        signal = engine.evaluate_token_signal("MintQ", "Q")

        self.assertEqual(signal.quote_quality, 0.50)
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
            token_amount=500.0,
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
        self.assertEqual(profile.netflow_usd, 100.0)

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
            quote_amount_usd=100000.0,
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
        self.assertEqual(res.imbalance_momentum_score, 100.0)

    def test_pool_age_is_based_on_pool_creation_timestamp(self):
        """Pool age must strictly represent: (current_observation_time - verified_pool_creation_time)."""
        now = time.time()
        pool_creation_ts = now - (3600.0)

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
        self.assertEqual(res.pool_age_minutes, 60.0)
        self.assertEqual(res.earlyness_score, 85.0)

    def test_swap_observation_window_cannot_be_used_as_pool_age(self):
        """Swap observation window (span of swap timestamps) cannot be used as pool age."""
        now = time.time()
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

        ctx = LiveTokenContext(
            mint="MintWin",
            symbol="WIN",
            pool_created_at=None,
            observed_at=now,
            price_usd=1.0,
            pool_liquidity_usd=50000.0,
            is_mint_verified_on_chain=True,
            is_market_data_verified=True
        )

        res = self.funnel.score_live_token(ctx, [s1, s2])
        self.assertIsNone(res.pool_age_minutes)
        self.assertEqual(res.earlyness_score, 50.0)
        self.assertEqual(res.confidence, 0.90)

    # =========================================================================
    # 2. Canonical Provenance & Synthetic Data Removal Tests (A - H)
    # =========================================================================

    def test_a_build_canonical_provenance_cannot_create_synthetic_real_rows(self):
        """A) build_canonical_provenance cannot create synthetic REAL rows when called with empty inputs."""
        res = build_canonical_provenance(live_tokens=[], live_swaps=[], output_dir=self.temp_dir)
        self.assertEqual(res["tokens_count"], 0)
        self.assertEqual(res["swaps_count"], 0)
        self.assertEqual(res["synthetic_rows"], 0)
        self.assertEqual(res["status"], "LIVE_DATA_UNAVAILABLE")

    def test_b_fake_generated_signatures_are_rejected(self):
        """B) Fake generated signatures are rejected by CanonicalProvenanceGuard."""
        invalid_swap = {
            "signature": "invalid_short_fake_sig",
            "slot": 100,
            "block_time": time.time(),
            "mint": "9BB6NFEcjBCtnNLFko2FqVQBq8HHM13kCyYcdQbgpump",
            "wallet_pubkey": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",
            "source_type": "REAL",
            "rpc_verified": 1,
            "observed_at": time.time()
        }
        is_val, msg = CanonicalProvenanceGuard.validate_swap_for_write(invalid_swap)
        self.assertFalse(is_val)

    def test_c_fake_generated_wallets_are_rejected(self):
        """C) Fake generated wallets (invalid Base58 length) are rejected."""
        invalid_wallet_swap = {
            "signature": "25X8h9xM1aB2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2g3h4i5j6k7l8m9n0",
            "slot": 100,
            "block_time": time.time(),
            "mint": "9BB6NFEcjBCtnNLFko2FqVQBq8HHM13kCyYcdQbgpump",
            "wallet_pubkey": "bad_wallet",
            "source_type": "REAL",
            "rpc_verified": 1,
            "observed_at": time.time()
        }
        is_val, msg = CanonicalProvenanceGuard.validate_swap_for_write(invalid_wallet_swap)
        self.assertFalse(is_val)

    def test_d_source_type_real_requires_runtime_provenance(self):
        """D) source_type=REAL strictly requires rpc_verified=True and valid timestamps."""
        unverified_real_swap = {
            "signature": "25X8h9xM1aB2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2g3h4i5j6k7l8m9n0",
            "slot": 100,
            "block_time": time.time(),
            "mint": "9BB6NFEcjBCtnNLFko2FqVQBq8HHM13kCyYcdQbgpump",
            "wallet_pubkey": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",
            "source_type": "REAL",
            "rpc_verified": 0,  # Unverified
            "observed_at": time.time()
        }
        is_val, msg = CanonicalProvenanceGuard.validate_swap_for_write(unverified_real_swap)
        self.assertFalse(is_val)

    def test_e_empty_live_input_produces_zero_rows(self):
        """E) Empty live input produces exactly zero database rows."""
        db_path = os.path.join(self.temp_dir, "solmeme_live_run.db")
        build_canonical_provenance(live_tokens=[], live_swaps=[], output_dir=self.temp_dir)
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM tokens")
        t_cnt = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM live_swaps")
        s_cnt = c.fetchone()[0]
        conn.close()
        self.assertEqual(t_cnt, 0)
        self.assertEqual(s_cnt, 0)

    def test_f_empty_live_input_cannot_produce_true_live(self):
        """F) Empty live input produces LIVE_DATA_UNAVAILABLE, never TRUE_LIVE."""
        res = execute_early_alpha_pipeline(live_tokens=[], swaps=[], output_dir=self.temp_dir)
        self.assertEqual(res["verdict"], "LIVE_DATA_UNAVAILABLE")
        self.assertNotEqual(res["verdict"], "TRUE_LIVE_EARLY_ALPHA_INTEGRITY")

    def test_g_fixture_replay_data_is_labeled_replay_or_test(self):
        """G) Fixture/replay test builder labels records REPLAY or TEST, never REAL."""
        fix_db = os.path.join(self.temp_dir, "fixture_test.db")
        create_test_fixture_db(fix_db, source_type="REPLAY")
        conn = sqlite3.connect(fix_db)
        c = conn.cursor()
        c.execute("SELECT DISTINCT source_type FROM tokens")
        src_types = [r[0] for r in c.fetchall()]
        conn.close()
        self.assertIn("REPLAY", src_types)
        self.assertNotIn("REAL", src_types)

    def test_h_live_canonical_db_contains_only_runtime_originated_records(self):
        """H) Live canonical DB accepts strictly validated runtime records."""
        valid_token = {
            "mint": "9BB6NFEcjBCtnNLFko2FqVQBq8HHM13kCyYcdQbgpump",
            "symbol": "FARTCOIN",
            "name": "Fartcoin",
            "price_usd": 0.115,
            "liquidity_usd": 3400000.0,
            "verification_status": "VERIFIED_ON_CHAIN",
            "source_type": "REAL",
            "pool_created_at": time.time() - 3600.0
        }
        res = build_canonical_provenance(live_tokens=[valid_token], live_swaps=[], output_dir=self.temp_dir)
        self.assertEqual(res["tokens_count"], 1)


if __name__ == "__main__":
    unittest.main()
