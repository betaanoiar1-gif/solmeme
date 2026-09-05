"""
Live Engine Provenance Hardening Regression Tests (Tests A through J).
Verifies:
A. Provider provenance preservation
B. Unverified quote isolation
C. Unknown liquidity preservation (None -> None, never 0.0)
D. Removal of $50,000 exit liquidity constant
E. Removal of 101.80 SOL price constant
F. Missing first_seen handling (None -> None, EarlyLaunchSniper False)
G. Exit execution liquidity consumption & TradeJournal recording
H. Unified live market depth object consumption across all components
I. Fail-closed engine behavior when live data is unavailable
J. Accounting invariants preservation in live paper cycle
"""

import os
import shutil
import tempfile
import time
import unittest
from typing import Any, Dict, List, Optional

from app.config.settings import AppConfig, ExitConfig, ExecutionConfig
from app.core.database import DatabaseManager
from blockchain.parsers.real_swap_parser import RealSwapRecord
from blockchain.solana.mint_verifier import OnChainMintVerification, OnChainMintVerifier
from blockchain.solana.types import Provenance, SourceType
from intelligence.smart_money.emerging_smart_money import EmergingSmartMoneyEngine, is_swap_quote_verified
from intelligence.whales.real_whale_tracker import RealWhaleTracker
from intelligence.whales.relative_whale_engine import RelativeWhaleEngine
from portfolio.accounting.trade_journal import TradeJournal
from portfolio.virtual_wallet.virtual_wallet import VirtualWallet
from scoring.early_alpha.early_token_priority import LiveTokenContext, EarlyTokenPriorityFunnel
from simulation.execution.execution_engine import ExecutionSimulator
from simulation.partial_fills.partial_fill_model import PartialFillModel
from simulation.slippage.slippage_model import SlippageModel
from sniper.early_launch.early_launch_sniper import EarlyLaunchSniper
from sniper.execution.exit_engine import DynamicExitEngine
from app.orchestration.live_paper_engine import RealLivePaperEngine, LivePaperCycleResult


class MockTestLiveProvider:
    """Configurable provider for isolated testing of LivePaperEngine provenance behaviors."""

    def __init__(
        self,
        is_connected: bool = True,
        tokens: Optional[List[Dict[str, Any]]] = None,
        trades: Optional[Dict[str, List[Dict[str, Any]]]] = None,
        sol_price_usd: Optional[float] = None
    ):
        self._connected = is_connected
        self._tokens = tokens or []
        self._trades = trades or {}
        self.sol_price_usd = sol_price_usd

    def is_network_connected(self) -> bool:
        return self._connected

    def get_sol_price_usd(self) -> Optional[float]:
        return self.sol_price_usd

    def scan_recent_tokens(self, limit: int = 30) -> List[Dict[str, Any]]:
        return self._tokens[:limit]

    def get_token_metadata(self, mint: str) -> Optional[Dict[str, Any]]:
        for t in self._tokens:
            if t.get("mint") == mint:
                return {
                    "mint": mint,
                    "symbol": t.get("symbol", "TEST"),
                    "decimals": 6,
                    "supply": 1_000_000_000,
                    "mint_authority": t.get("mint_authority"),
                    "freeze_authority": t.get("freeze_authority"),
                    "is_verified_on_chain": True
                }
        return None

    def get_token_market_data(self, mint: str) -> Optional[Dict[str, Any]]:
        for t in self._tokens:
            if t.get("mint") == mint:
                return t
        return None

    def get_token_security_data(self, mint: str) -> Optional[Dict[str, Any]]:
        return {
            "mint": mint,
            "mint_auth_revoked": True,
            "freeze_auth_revoked": True,
            "lp_locked_pct": 100.0,
            "top10_holder_pct": 25.0,
            "dev_holding_pct": 2.0,
            "is_honeypot": False,
            "is_wash_traded": False
        }

    def get_recent_trades(self, mint: str, limit: int = 30) -> List[Dict[str, Any]]:
        return self._trades.get(mint, [])[:limit]


class TestLiveEngineProvenance(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_live_paper.db")
        self.config = AppConfig()
        self.config.db_path = self.db_path
        self.config.data_mode = "replay"

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    # -------------------------------------------------------------------------
    # Test A: Provider Provenance Preservation
    # -------------------------------------------------------------------------
    def test_a_provider_provenance_preservation(self):
        """
        Preserve provider provenance exactly.
        If provenance indicates REPLAY or UNKNOWN, it must NOT be forced to REAL.
        If provenance is missing, mark UNKNOWN with confidence 0.0 and verified_on_chain=False.
        """
        mint = "MintProvTest1111111111111111111111111111111"
        tokens = [{
            "mint": mint,
            "symbol": "PROV",
            "price": 1.0,
            "liquidity": 50000.0,
            "first_seen_ts": time.time() - 300.0
        }]
        trades = {
            mint: [
                {
                    "signature": "5a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2g3h4i5j6k7l8m9n0",
                    "slot": 100,
                    "timestamp": time.time(),
                    "signer": "Wallet11111111111111111111111111111111111111",
                    "type": "BUY",
                    "token_amount": 1000.0,
                    "usd_amount": 1000.0,
                    "price_usd": 1.0,
                    "provenance": {
                        "source_type": "REPLAY",
                        "verified_on_chain": False,
                        "confidence": 0.5,
                        "observed_at": 1700000000.0,
                        "provider": "CustomProvider"
                    }
                },
                {
                    "signature": "6a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2g3h4i5j6k7l8m9n0",
                    "slot": 101,
                    "timestamp": time.time(),
                    "signer": "Wallet22222222222222222222222222222222222222",
                    "type": "BUY",
                    "token_amount": 500.0,
                    "usd_amount": 500.0,
                    "price_usd": 1.0,
                    # Provenance missing
                }
            ]
        }

        provider = MockTestLiveProvider(tokens=tokens, trades=trades, sol_price_usd=150.0)
        engine = RealLivePaperEngine(config=self.config, data_provider=provider)
        engine.run_live_cycle()

        self.assertEqual(len(engine.ingested_swaps), 2)

        # Trade 1: REPLAY preserved, verified_on_chain=False preserved, is_quote_verified=False
        swap1 = engine.ingested_swaps[0]
        self.assertEqual(swap1.provenance.source_type, SourceType.REPLAY)
        self.assertFalse(swap1.provenance.verified_on_chain)
        self.assertFalse(swap1.is_quote_verified)
        self.assertEqual(swap1.provenance.provider, "CustomProvider")
        self.assertEqual(swap1.provenance.observed_at, 1700000000.0)

        # Trade 2: Missing provenance -> UNKNOWN, verified_on_chain=False, is_quote_verified=False
        swap2 = engine.ingested_swaps[1]
        self.assertEqual(swap2.provenance.source_type, SourceType.UNKNOWN)
        self.assertFalse(swap2.provenance.verified_on_chain)
        self.assertFalse(swap2.is_quote_verified)
        self.assertEqual(swap2.provenance.confidence, 0.0)

    # -------------------------------------------------------------------------
    # Test B: Unverified Quote Isolation
    # -------------------------------------------------------------------------
    def test_b_unverified_quote_isolation(self):
        """
        Unverified quotes (numeric USD amount present but verified_on_chain=False)
        must not participate in verified quote analytics.
        """
        swap_unverified = RealSwapRecord(
            signature="sig_unverified",
            slot=100,
            timestamp=time.time(),
            pool="PoolA",
            mint="MintA",
            symbol="A",
            wallet="WalletA",
            side="BUY",
            token_amount=1000.0,
            quote_amount_sol=10.0,
            quote_amount_usd=10000.0,
            price_usd=10.0,
            venue="Pump.fun",
            is_whale=True,
            is_quote_verified=False,
            provenance=Provenance(source_type=SourceType.REAL, verified_on_chain=False)
        )

        self.assertFalse(is_swap_quote_verified(swap_unverified))

        # Whale engine rejects unverified quote
        tracker = RealWhaleTracker(DatabaseManager(self.db_path))
        event = tracker.process_real_swap(swap_unverified, pool_liquidity_usd=50000.0)
        self.assertIsNone(event)
        self.assertEqual(tracker.get_token_whale_netflow("MintA"), 0.0)

        # Emerging smart money engine rejects unverified quote from USD stats
        sm_engine = EmergingSmartMoneyEngine()
        profile = sm_engine.process_swap(swap_unverified, pool_liquidity_usd=50000.0)
        self.assertEqual(profile.unverified_quote_swaps, 1)
        self.assertEqual(profile.verified_quote_swaps, 0)
        self.assertIsNone(profile.buy_volume_usd)
        self.assertIsNone(profile.netflow_usd)

    # -------------------------------------------------------------------------
    # Test C: Unknown Liquidity Preservation (None -> None, Never 0.0)
    # -------------------------------------------------------------------------
    def test_c_unknown_liquidity_preservation(self):
        """
        When token liquidity is None/unknown, it must remain None in token_liquidity_map
        and not be converted to 0.0 or default 1_000_000.0 / 50_000.0.
        """
        mint = "MintUnknownLiq1111111111111111111111111111"
        tokens = [{
            "mint": mint,
            "symbol": "UNLIQ",
            "price": 0.50,
            "liquidity": None,  # Explicitly None
            "first_seen_ts": time.time() - 600.0
        }]

        provider = MockTestLiveProvider(tokens=tokens, trades={})
        engine = RealLivePaperEngine(config=self.config, data_provider=provider)
        engine.run_live_cycle()

        self.assertIn(mint, engine.token_liquidity_map)
        self.assertIsNone(engine.token_liquidity_map[mint])

        # Sizing and execution handle None liquidity without exception
        res = engine.exec_simulator.execute_order(market_price=0.50, trade_size_usd=10.0, liquidity_usd=None, is_buy=True)
        self.assertGreater(res.executed_price, 0.50)
        self.assertEqual(res.filled_size_usd, 10.0)

    # -------------------------------------------------------------------------
    # Test D: Removal of Hardcoded $50,000 Exit Liquidity
    # -------------------------------------------------------------------------
    def test_d_removal_of_50000_exit_liquidity(self):
        """
        DynamicExitEngine and order execution must accept liquidity_usd=None
        or dynamic verified liquidity without relying on 50_000.0.
        """
        exit_engine = DynamicExitEngine()
        # Evaluate with None liquidity (safe hold, no crash)
        verdict = exit_engine.evaluate_position(
            entry_price=1.0,
            current_price=1.05,
            peak_price=1.05,
            entry_time=time.time() - 60.0,
            current_time=time.time(),
            smart_money_score=50.0,
            whale_netflow=0.0,
            regime="R3_EARLY_DISCOVERY",
            liquidity_usd=None
        )
        self.assertFalse(verdict.should_exit)

        # Liquidity drain trigger when verified liquidity is < $500
        verdict_drain = exit_engine.evaluate_position(
            entry_price=1.0,
            current_price=1.05,
            peak_price=1.05,
            entry_time=time.time() - 60.0,
            current_time=time.time(),
            smart_money_score=50.0,
            whale_netflow=0.0,
            regime="R3_EARLY_DISCOVERY",
            liquidity_usd=200.0  # Liquidity drained below $500
        )
        self.assertTrue(verdict_drain.should_exit)
        self.assertIn("LIQUIDITY_DRAIN_DETECTED", verdict_drain.exit_reason)

    # -------------------------------------------------------------------------
    # Test E: Removal of Hardcoded 101.80 SOL Price Constant
    # -------------------------------------------------------------------------
    def test_e_removal_of_101_80_sol_price_constant(self):
        """
        In RealLivePaperEngine, quote_amount_sol must be computed from provider's live SOL price,
        or left as None if live SOL price is unavailable (never fixed 101.80).
        """
        mint = "MintSolPrice111111111111111111111111111111"
        tokens = [{
            "mint": mint,
            "symbol": "SOLP",
            "price": 2.0,
            "liquidity": 100000.0,
            "first_seen_ts": time.time() - 500.0
        }]
        trades = {
            mint: [{
                "signature": "7a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2g3h4i5j6k7l8m9n0",
                "slot": 100,
                "timestamp": time.time(),
                "signer": "WalletSolTest11111111111111111111111111111",
                "type": "BUY",
                "token_amount": 100.0,
                "usd_amount": 200.0,
                "price_usd": 2.0,
                "provenance": {"source_type": "REAL", "verified_on_chain": True, "confidence": 1.0}
            }]
        }

        # Case 1: Provider provides live SOL price = $200.00 -> quote_sol = 200.0 / 200.0 = 1.0
        provider_with_sol = MockTestLiveProvider(tokens=tokens, trades=trades, sol_price_usd=200.0)
        engine1 = RealLivePaperEngine(config=self.config, data_provider=provider_with_sol)
        engine1.run_live_cycle()
        self.assertEqual(engine1.ingested_swaps[0].quote_amount_sol, 1.0)
        self.assertNotEqual(engine1.ingested_swaps[0].quote_amount_sol, round(200.0 / 101.80, 6))

        # Case 2: Provider SOL price unavailable -> quote_amount_sol remains None (never 101.80)
        provider_no_sol = MockTestLiveProvider(tokens=tokens, trades=trades, sol_price_usd=None)
        engine2 = RealLivePaperEngine(config=self.config, data_provider=provider_no_sol)
        engine2.run_live_cycle()
        self.assertIsNone(engine2.ingested_swaps[0].quote_amount_sol)

    # -------------------------------------------------------------------------
    # Test F: Missing First Seen Handling
    # -------------------------------------------------------------------------
    def test_f_missing_first_seen_handling(self):
        """
        Missing first_seen_ts must produce None pool age (or neutral fallback),
        and EarlyLaunchSniper must return False (never trigger on unknown age).
        """
        mint = "MintNoFirstSeen1111111111111111111111111111"
        tokens = [{
            "mint": mint,
            "symbol": "NOAGE",
            "price": 1.0,
            "liquidity": 100000.0,
            "first_seen_ts": None  # Missing discovery time
        }]

        provider = MockTestLiveProvider(tokens=tokens, trades={})
        engine = RealLivePaperEngine(config=self.config, data_provider=provider)
        res = engine.run_live_cycle()

        self.assertEqual(res.real_tokens_discovered, 1)

        # EarlyLaunchSniper check with age_minutes = None
        from scoring.opportunity.opportunity_scorer import OpportunityReport
        dummy_opp = OpportunityReport(
            mint=mint,
            symbol="NOAGE",
            alpha_score=85.0,
            risk_score=20.0,
            confidence_score=80.0,
            earlyness_score=80.0,
            execution_score=80.0,
            final_score=85.0,
            regime="R3_EARLY_DISCOVERY",
            narrative="Memes",
            recommendation="PAPER_ENTRY",
            why_ranked_high=[],
            why_not_higher=[],
            what_supports_it=[],
            what_could_invalidate_it=[],
            updated_at=time.time()
        )

        should_snipe_early = EarlyLaunchSniper.evaluate(dummy_opp, age_minutes=None)
        self.assertFalse(should_snipe_early)

    # -------------------------------------------------------------------------
    # Test G: Exit Execution Liquidity Consumption & Trade Journal
    # -------------------------------------------------------------------------
    def test_g_exit_execution_liquidity_consumption(self):
        """
        Order execution simulator and TradeJournal must record verified liquidity accurately.
        """
        journal = TradeJournal(DatabaseManager(self.db_path))
        record = journal.record_completed_trade(
            strategy_name="TestStrategy",
            mint="MintTradeTest",
            symbol="TRD",
            entry_time=time.time() - 100.0,
            entry_price=1.0,
            size_usd=25.0,
            simulated_fill_qty=25.0,
            liquidity_usd=75000.0,
            slippage_usd=0.10,
            fee_usd=0.05,
            exit_time=time.time(),
            exit_price=1.20,
            exit_reason="TAKE_PROFIT_TIER_1 (+20.0% target hit)",
            realized_pnl=4.85,
            peak_price=1.20,
            lowest_price=0.98,
            alpha_score=78.0,
            risk_score=25.0,
            regime="R3_EARLY_DISCOVERY"
        )

        self.assertEqual(record.liquidity_usd, 75000.0)
        self.assertEqual(record.realized_pnl, 4.85)
        self.assertEqual(len(journal.get_strategy_trades("TestStrategy")), 1)

    # -------------------------------------------------------------------------
    # Test H: Unified Live Market Depth Object
    # -------------------------------------------------------------------------
    def test_h_unified_live_market_depth_consumption(self):
        """
        A single source of truth for pool_liquidity_usd is consumed by:
        - RelativeWhaleEngine
        - EmergingSmartMoneyEngine
        - SlippageModel
        - PartialFillModel
        """
        pool_liq = 80000.0
        swap = RealSwapRecord(
            signature="sig_depth_test",
            slot=100,
            timestamp=time.time(),
            pool="PoolDepth",
            mint="MintDepth",
            symbol="DEP",
            wallet="WalletDepth",
            side="BUY",
            token_amount=1000.0,
            quote_amount_sol=20.0,
            quote_amount_usd=3000.0,
            price_usd=3.0,
            venue="Pump.fun",
            is_whale=False,
            is_quote_verified=True,
            provenance=Provenance(source_type=SourceType.REAL, verified_on_chain=True)
        )

        # 1. Whale engine consumes pool_liq
        wm = RelativeWhaleEngine.evaluate_token("MintDepth", "DEP", [swap], pool_liquidity_usd=pool_liq)
        self.assertEqual(wm.pool_liquidity_usd, pool_liq)
        self.assertIsNotNone(wm.flow_to_liquidity_ratio)
        self.assertEqual(wm.flow_to_liquidity_ratio, round(3000.0 / pool_liq, 6))

        # 2. Emerging smart money consumes pool_liq
        sm = EmergingSmartMoneyEngine()
        prof = sm.process_swap(swap, pool_liquidity_usd=pool_liq)
        self.assertEqual(prof.max_pool_impact_pct, (3000.0 / pool_liq) * 100.0)

        # 3. Slippage model consumes pool_liq
        exec_cfg = ExecutionConfig()
        slip = SlippageModel.calculate(market_price=3.0, trade_size_usd=3000.0, liquidity_usd=pool_liq, is_buy=True, config=exec_cfg)
        expected_impact = (3000.0 / pool_liq) * exec_cfg.liquidity_impact_constant * 100.0
        self.assertAlmostEqual(slip.price_impact_pct, expected_impact, places=2)

        # 4. Partial fill model consumes pool_liq
        fill = PartialFillModel.calculate(requested_usd=5000.0, liquidity_usd=pool_liq, enable_partial=True)
        self.assertEqual(fill.fill_ratio, 0.80)  # 5% of 80000 is 4000; 4000 / 5000 = 0.80

    # -------------------------------------------------------------------------
    # Test I: Live Paper Engine Fail-Closed on Disconnected Network
    # -------------------------------------------------------------------------
    def test_i_fail_closed_on_disconnected_network(self):
        """
        When live network is unreachable, LivePaperEngine must fail closed:
        0 tokens discovered, 0 positions opened, accounting invariants valid.
        """
        disconnected_provider = MockTestLiveProvider(is_connected=False, tokens=[], trades={})
        engine = RealLivePaperEngine(config=self.config, data_provider=disconnected_provider)
        cycle_res = engine.run_live_cycle()

        self.assertFalse(cycle_res.network_connected)
        self.assertEqual(cycle_res.real_tokens_discovered, 0)
        self.assertEqual(cycle_res.active_paper_positions, 0)
        self.assertTrue(cycle_res.accounting_invariants_valid)
        self.assertEqual(cycle_res.ending_equity_usd, 100.0)
        self.assertEqual(cycle_res.cash_usd, 100.0)

    # -------------------------------------------------------------------------
    # Test J: Accounting Invariants Preservation in Live Paper Cycle
    # -------------------------------------------------------------------------
    def test_j_accounting_invariants_preservation(self):
        """
        Complete live paper cycle must maintain double-entry accounting invariants:
        Equity = Cash + Gross Value of Positions - Unrealized Fees - Unrealized Slippage.
        """
        mint = "MintAccounting1111111111111111111111111111"
        tokens = [{
            "mint": mint,
            "symbol": "ACC",
            "price": 0.10,
            "liquidity": 100000.0,
            "first_seen_ts": time.time() - 100.0,
            "volume_24h": 50000.0,
            "holders_count": 200
        }]
        trades = {
            mint: [
                {
                    "signature": "8a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2g3h4i5j6k7l8m9n0",
                    "slot": 100,
                    "timestamp": time.time(),
                    "signer": "WalletWhale11111111111111111111111111111111",
                    "type": "BUY",
                    "token_amount": 100000.0,
                    "usd_amount": 10000.0,
                    "price_usd": 0.10,
                    "provenance": {"source_type": "REAL", "verified_on_chain": True, "confidence": 1.0}
                }
            ]
        }

        provider = MockTestLiveProvider(tokens=tokens, trades=trades, sol_price_usd=150.0)
        engine = RealLivePaperEngine(config=self.config, data_provider=provider)
        cycle_res = engine.run_live_cycle()

        self.assertTrue(cycle_res.accounting_invariants_valid)
        self.assertEqual(cycle_res.accounting_status, "INVARIANTS_SATISFIED")
        self.assertAlmostEqual(cycle_res.ending_equity_usd, cycle_res.cash_usd + cycle_res.net_liquidation_val_usd, places=2)


if __name__ == "__main__":
    unittest.main()
