import unittest
from blockchain.parsers.real_swap_parser import RealSwapRecord
from intelligence.smart_money.emerging_smart_money import EmergingSmartMoneyEngine, EmergingWalletProfile
from intelligence.whales.relative_whale_engine import RelativeWhaleEngine, RelativeWhaleMetrics
from scoring.early_alpha.early_token_priority import EarlyTokenPriorityFunnel

class TestEarlyAlphaEngine(unittest.TestCase):

    def setUp(self):
        self.es_engine = EmergingSmartMoneyEngine()
        self.funnel = EarlyTokenPriorityFunnel()

    def test_emerging_smart_money_accumulation(self):
        s1 = RealSwapRecord(
            signature="sig1",
            slot=1000,
            timestamp=1700000000.0,
            pool="POOL1",
            mint="MINT1",
            symbol="TEST1",
            wallet="wallet_alpha",
            side="BUY",
            token_amount=25000.0,
            quote_amount_sol=25.0,
            quote_amount_usd=2500.0,
            price_usd=0.1,
            venue="Pump.fun"
        )
        s2 = RealSwapRecord(
            signature="sig2",
            slot=1010,
            timestamp=1700000010.0,
            pool="POOL1",
            mint="MINT1",
            symbol="TEST1",
            wallet="wallet_alpha",
            side="BUY",
            token_amount=50000.0,
            quote_amount_sol=50.0,
            quote_amount_usd=5000.0,
            price_usd=0.1,
            venue="Pump.fun"
        )
        s3 = RealSwapRecord(
            signature="sig3",
            slot=1020,
            timestamp=1700000020.0,
            pool="POOL1",
            mint="MINT1",
            symbol="TEST1",
            wallet="wallet_alpha",
            side="BUY",
            token_amount=125000.0,
            quote_amount_sol=125.0,
            quote_amount_usd=12500.0,
            price_usd=0.1,
            venue="Pump.fun"
        )
        
        self.es_engine.process_swap(s1, pool_liquidity_usd=100_000.0)
        self.es_engine.process_swap(s2, pool_liquidity_usd=100_000.0)
        profile = self.es_engine.process_swap(s3, pool_liquidity_usd=100_000.0)
        
        self.assertEqual(profile.buy_count, 3)
        self.assertEqual(profile.sell_count, 0)
        self.assertGreater(profile.emerging_smart_money_score, 70.0)
        self.assertTrue(profile.is_emerging_smart_money)

    def test_relative_whale_strength_continuous(self):
        swaps = [
            RealSwapRecord(
                signature="wsig1",
                slot=1000,
                timestamp=1700000000.0,
                pool="POOL_TEST",
                mint="MINT_TEST",
                symbol="TEST",
                wallet="whale_1",
                side="BUY",
                token_amount=50000.0,
                quote_amount_sol=50.0,
                quote_amount_usd=5000.0,
                price_usd=0.1,
                venue="Pump.fun"
            ),
            RealSwapRecord(
                signature="wsig2",
                slot=1010,
                timestamp=1700000010.0,
                pool="POOL_TEST",
                mint="MINT_TEST",
                symbol="TEST",
                wallet="whale_2",
                side="BUY",
                token_amount=70000.0,
                quote_amount_sol=70.0,
                quote_amount_usd=7000.0,
                price_usd=0.1,
                venue="Pump.fun"
            ),
            RealSwapRecord(
                signature="wsig3",
                slot=1020,
                timestamp=1700000020.0,
                pool="POOL_TEST",
                mint="MINT_TEST",
                symbol="TEST",
                wallet="whale_1",
                side="BUY",
                token_amount=48000.0,
                quote_amount_sol=48.0,
                quote_amount_usd=4800.0,
                price_usd=0.1,
                venue="Pump.fun"
            )
        ]
        metrics = RelativeWhaleEngine.evaluate_token(
            mint="MINT_TEST",
            symbol="TEST",
            swaps=swaps,
            pool_liquidity_usd=50000.0
        )
        self.assertGreater(metrics.relative_whale_strength_score, 65.0)
        self.assertIn(metrics.conviction_tier, ["MEGA_WHALE_ACCUMULATION", "HIGH_RELATIVE_CONVICTION"])
        self.assertGreater(metrics.flow_to_liquidity_ratio, 0.20)

    def test_early_token_funnel_scoring(self):
        token_info = {
            "mint": "MINT_EARLY",
            "symbol": "EARLY",
            "pool_liquidity_usd": 150000.0,
            "is_frozen": False,
            "is_honeypot": False,
            "security_hard_reject": False,
            "mint_authority": None,
            "freeze_authority": None,
            "top_holder_pct": 0.08,
            "verified_buy_volume_usd": 25000.0,
            "verified_sell_volume_usd": 5000.0,
            "verified_unique_buyers": 12,
            "verified_unique_sellers": 3,
            "pool_age_minutes": 15.0
        }
        res = self.funnel.score_token_lightweight(token_info)
        self.assertEqual(res.stage, "DEEP_ANALYSIS_PRIORITIZED")
        self.assertGreater(res.early_alpha_score, 60.0)
        self.assertFalse(res.security_hard_reject)

if __name__ == "__main__":
    unittest.main()
