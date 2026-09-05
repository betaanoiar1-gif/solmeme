import os
import sys
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
)


class TestEarlyAlphaEngine(unittest.TestCase):

    def setUp(self):
        self.es_engine = EmergingSmartMoneyEngine()
        self.funnel = EarlyTokenPriorityFunnel()

    def test_static_all_42_list_cannot_be_accessed_by_live_mode(self):
        """Proves static ALL_42 list is not present in early_token_priority module."""
        import scoring.early_alpha.early_token_priority as ep
        self.assertFalse(hasattr(ep, "ALL_42_VERIFIED_TOKENS"), "ALL_42_VERIFIED_TOKENS must not exist in live module")
        self.assertFalse(hasattr(ep, "STATIC_TOKENS"), "STATIC_TOKENS must not exist in live module")

    def test_live_mode_with_empty_discovery_produces_zero_tokens(self):
        """Proves live mode with empty discovery produces zero tokens without static fallback."""
        results = self.funnel.score_tokens([])
        self.assertEqual(len(results), 0)

        test_dir = "reports/test_empty"
        pipe_res = execute_early_alpha_pipeline(live_tokens=[], swaps=[], output_dir=test_dir)
        self.assertEqual(pipe_res["discovered"], 0)
        self.assertEqual(pipe_res["scored"], 0)
        self.assertEqual(pipe_res["static_data_used"], 0)
        self.assertEqual(pipe_res["verdict"], "TRUE_LIVE_EARLY_ALPHA")
        if os.path.exists(test_dir):
            import shutil
            shutil.rmtree(test_dir)

    def test_live_token_data_flows_dynamically_into_score_engine(self):
        """Proves dynamic LiveTokenContext flows directly through scoring."""
        ctx = LiveTokenContext(
            mint="DynamicMint1111111111111111111111111111111",
            symbol="DYN",
            name="Dynamic Token",
            discovered_at=time.time() - 300,
            verified_at=time.time(),
            price_usd=0.05,
            pool_liquidity_usd=100000.0,
            pool_address="DynPool111",
            venue="Pump.fun",
            pool_age_minutes=5.0,
            mint_authority=None,
            freeze_authority=None,
            top_holder_pct=15.0,
            security_status="VERIFIED_SAFE",
            swap_count=3,
            buy_volume_usd=15000.0,
            sell_volume_usd=2000.0,
            netflow_usd=13000.0,
            is_mint_verified_on_chain=True,
            is_market_data_verified=True,
            is_security_verified=True,
            security_hard_reject=False,
            quote_quality=1.0,
            source_type=SourceType.REAL,
            confidence=1.0
        )

        swaps = [
            RealSwapRecord(
                signature="dynsig1",
                slot=1000,
                timestamp=time.time() - 200,
                pool="DynPool111",
                mint=ctx.mint,
                symbol="DYN",
                wallet="wallet_alpha",
                side="BUY",
                token_amount=100000.0,
                quote_amount_sol=50.0,
                quote_amount_usd=5000.0,
                price_usd=0.05,
                venue="Pump.fun",
                is_whale=True,
                is_quote_verified=True
            ),
            RealSwapRecord(
                signature="dynsig2",
                slot=1010,
                timestamp=time.time() - 100,
                pool="DynPool111",
                mint=ctx.mint,
                symbol="DYN",
                wallet="wallet_alpha",
                side="BUY",
                token_amount=200000.0,
                quote_amount_sol=100.0,
                quote_amount_usd=10000.0,
                price_usd=0.05,
                venue="Pump.fun",
                is_whale=True,
                is_quote_verified=True
            )
        ]

        engine = EmergingSmartMoneyEngine()
        for s in swaps:
            engine.process_swap(s, pool_liquidity_usd=100000.0)

        res = self.funnel.score_live_token(ctx, swaps, emerging_engine=engine)
        self.assertEqual(res.mint, ctx.mint)
        self.assertEqual(res.symbol, "DYN")
        self.assertGreater(res.lightweight_early_alpha_score, 60.0)
        self.assertEqual(res.pipeline_stage, "DEEP_ANALYSIS_PRIORITIZED")
        self.assertEqual(res.action_recommendation, "PRIORITY_DEEP_EVAL")

    def test_unknown_liquidity_does_not_become_1m(self):
        """Proves unknown liquidity does NOT default to $1,000,000 in any engine."""
        swap = RealSwapRecord(
            signature="test_sig_liq",
            slot=1000,
            timestamp=time.time(),
            pool="UnknownPool",
            mint="UnknownMint",
            symbol="UNK",
            wallet="test_wallet",
            side="BUY",
            token_amount=1000.0,
            quote_amount_sol=10.0,
            quote_amount_usd=1000.0,
            price_usd=1.0,
            venue="Pump.fun",
            is_quote_verified=True
        )

        # 1. Emerging Smart Money Engine
        profile = self.es_engine.process_swap(swap, pool_liquidity_usd=None)
        self.assertIsNone(profile.max_pool_impact_pct, "Max pool impact must be None when pool liquidity is unknown")

        # 2. Relative Whale Engine
        metrics = RelativeWhaleEngine.evaluate_token("UnknownMint", "UNK", [swap], pool_liquidity_usd=None)
        self.assertIsNone(metrics.pool_liquidity_usd, "Pool liquidity must remain None")
        self.assertIsNone(metrics.flow_to_liquidity_ratio, "Flow to liquidity ratio must be None")
        self.assertIsNone(metrics.single_order_pool_impact_pct, "Single order pool impact must be None")

        # 3. Funnel
        ctx = LiveTokenContext(
            mint="UnknownMint",
            symbol="UNK",
            pool_liquidity_usd=None
        )
        res = self.funnel.score_live_token(ctx, [swap])
        self.assertIsNone(res.pool_liquidity_usd, "Result pool liquidity must remain None")

    def test_unknown_usd_quote_does_not_become_0(self):
        """Proves unknown USD quotes do NOT become 0.0 or pollute volume calculations."""
        swap_unverified = RealSwapRecord(
            signature="test_sig_no_quote",
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

        # 1. Emerging Smart Money Engine
        profile = self.es_engine.process_swap(swap_unverified, pool_liquidity_usd=50000.0)
        self.assertEqual(profile.unverified_quote_swaps, 1)
        self.assertEqual(profile.verified_quote_swaps, 0)
        self.assertIsNone(profile.buy_volume_usd, "Buy volume must remain None, not 0.0")
        self.assertIsNone(profile.netflow_usd, "Netflow must remain None, not 0.0")

        # 2. Relative Whale Engine
        metrics = RelativeWhaleEngine.evaluate_token("Mint1", "M1", [swap_unverified], pool_liquidity_usd=50000.0)
        self.assertEqual(metrics.absolute_netflow_usd, 0.0)
        self.assertEqual(metrics.accumulating_whales_count, 0)

    def test_every_score_has_live_provenance(self):
        """Proves all Early Alpha score results contain strict runtime provenance fields."""
        ctx = LiveTokenContext(
            mint="MintProvenanceTest11111111111111111111",
            symbol="PROV",
            pool_liquidity_usd=50000.0,
            is_mint_verified_on_chain=True,
            is_market_data_verified=True,
            source_type=SourceType.REAL,
            observed_at=time.time(),
            data_timestamp=time.time() - 60,
            quote_quality=1.0,
            confidence=1.0
        )
        res = self.funnel.score_live_token(ctx, [])
        self.assertEqual(res.source_type, "REAL")
        self.assertTrue(res.mint_verified_on_chain)
        self.assertTrue(res.market_data_verified)
        self.assertGreater(res.observed_at, 0)
        self.assertGreater(res.data_timestamp, 0)
        self.assertEqual(res.quote_quality, 1.0)
        self.assertEqual(res.confidence, 1.0)

    def test_security_hard_rejects_remain_unchanged(self):
        """Proves security hard rejects (active mint/freeze auth, high concentration) are strictly enforced."""
        # Active mint authority
        ctx_mint_auth = LiveTokenContext(
            mint="BadMint11111111111111111111111111111111",
            symbol="BAD_MINT",
            mint_authority="ActiveAuthority11111111111111111111111111"
        )
        res1 = self.funnel.score_live_token(ctx_mint_auth, [])
        self.assertTrue(res1.security_hard_reject)
        self.assertEqual(res1.pipeline_stage, "SECURITY_REJECTED")
        self.assertEqual(res1.action_recommendation, "HARD_REJECT")

        # Active freeze authority (honeypot)
        ctx_freeze_auth = LiveTokenContext(
            mint="BadFreeze1111111111111111111111111111111",
            symbol="BAD_FREEZE",
            freeze_authority="ActiveFreeze111111111111111111111111111"
        )
        res2 = self.funnel.score_live_token(ctx_freeze_auth, [])
        self.assertTrue(res2.security_hard_reject)
        self.assertEqual(res2.pipeline_stage, "SECURITY_REJECTED")
        self.assertEqual(res2.action_recommendation, "HARD_REJECT")

        # Top 10 concentration > 70%
        ctx_conc = LiveTokenContext(
            mint="BadConc11111111111111111111111111111111",
            symbol="BAD_CONC",
            top_holder_pct=85.0
        )
        res3 = self.funnel.score_live_token(ctx_conc, [])
        self.assertTrue(res3.security_hard_reject)
        self.assertEqual(res3.pipeline_stage, "SECURITY_REJECTED")
        self.assertEqual(res3.action_recommendation, "HARD_REJECT")


if __name__ == "__main__":
    unittest.main()
