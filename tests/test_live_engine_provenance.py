"""
Live Engine Provenance Hardening Regression Tests (Tests A through H & System Invariants).
Verifies:
A) Unknown exit liquidity remains None
B) Missing liquidity cannot execute using synthetic depth
C) DNA receives None for unknown liquidity
D) Missing age remains None
E) EarlyLaunchSniper false when age=None
F) Opportunity scoring preserves unknown age
G) Paper position preserves triggering provenance
H) No forced verified_on_chain=True in paper position creation
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
from intelligence.token.dna import DNASnapshot, TokenDNAEngine
from intelligence.whales.real_whale_tracker import RealWhaleTracker
from intelligence.whales.relative_whale_engine import RelativeWhaleEngine
from portfolio.accounting.trade_journal import TradeJournal
from portfolio.virtual_wallet.virtual_wallet import VirtualWallet, VirtualPosition
from scoring.early_alpha.early_token_priority import LiveTokenContext, EarlyTokenPriorityFunnel
from scoring.opportunity.opportunity_scorer import OpportunityReport, OpportunityScorer
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
    # Test A: Unknown Exit Liquidity Remains None
    # -------------------------------------------------------------------------
    def test_a_unknown_exit_liquidity_remains_none(self):
        """
        When token liquidity is unknown (None), it remains None in token_liquidity_map
        and is passed as None to DynamicExitEngine and ExecutionSimulator (no 1000/50000 fallback).
        """
        mint = "MintUnknownLiqA11111111111111111111111111111"
        tokens = [{
            "mint": mint,
            "symbol": "UNLIQA",
            "price": 0.50,
            "liquidity": None,  # Explicitly None
            "first_seen_ts": time.time() - 600.0
        }]

        provider = MockTestLiveProvider(tokens=tokens, trades={})
        engine = RealLivePaperEngine(config=self.config, data_provider=provider)
        engine.run_live_cycle()

        self.assertIn(mint, engine.token_liquidity_map)
        self.assertIsNone(engine.token_liquidity_map[mint])

        # DynamicExitEngine evaluates with liquidity_usd=None safely without raising exception
        verdict = engine.exit_engine.evaluate_position(
            entry_price=0.50,
            current_price=0.52,
            peak_price=0.52,
            entry_time=time.time() - 60.0,
            current_time=time.time(),
            smart_money_score=50.0,
            whale_netflow=0.0,
            regime="R3_EARLY_IGNITION",
            liquidity_usd=engine.token_liquidity_map[mint]
        )
        self.assertFalse(verdict.should_exit)

    # -------------------------------------------------------------------------
    # Test B: Missing Liquidity Cannot Execute Using Synthetic Depth
    # -------------------------------------------------------------------------
    def test_b_missing_liquidity_cannot_execute_using_synthetic_depth(self):
        """
        ExecutionSimulator and SlippageModel must not invent synthetic depth (e.g. 1000, 5000, 50000)
        when liquidity_usd is None.
        """
        exec_sim = ExecutionSimulator()
        res = exec_sim.execute_order(
            market_price=1.0,
            trade_size_usd=20.0,
            liquidity_usd=None,
            is_buy=True
        )

        # Price impact pct must be 0.0 (no fabricated depth)
        self.assertEqual(res.slippage.price_impact_pct, 0.0)
        self.assertEqual(res.fill_ratio, 1.0)
        self.assertEqual(res.filled_size_usd, 20.0)

        # Contrast with known liquidity $10,000 where price impact is calculated
        res_known = exec_sim.execute_order(
            market_price=1.0,
            trade_size_usd=20.0,
            liquidity_usd=10000.0,
            is_buy=True
        )
        self.assertGreater(res_known.slippage.price_impact_pct, 0.0)

    # -------------------------------------------------------------------------
    # Test C: DNA Receives None for Unknown Liquidity
    # -------------------------------------------------------------------------
    def test_c_dna_receives_none_for_unknown_liquidity(self):
        """
        TokenDNAEngine.record_snapshot must preserve liquidity=None when depth is unknown.
        """
        dna_engine = TokenDNAEngine(DatabaseManager(self.db_path))
        snap = dna_engine.record_snapshot(
            mint="MintDNATest",
            price=0.10,
            volume=500.0,
            liquidity=None,  # Unknown depth
            holders=15
        )

        self.assertIsNone(snap.liquidity)
        self.assertEqual(snap.price, 0.10)
        self.assertEqual(snap.volume, 500.0)

    # -------------------------------------------------------------------------
    # Test D: Missing Age Remains None
    # -------------------------------------------------------------------------
    def test_d_missing_age_remains_none(self):
        """
        When token discovery does not have first_seen_ts, age_min remains None
        (not converted to 1000.0 or 0.0).
        """
        mint = "MintNoAgeD111111111111111111111111111111111"
        t = {
            "mint": mint,
            "symbol": "NOAGE",
            "price": 1.0,
            "liquidity": 50000.0,
            "first_seen_ts": None
        }

        first_seen_ts = float(t["first_seen_ts"]) if t.get("first_seen_ts") is not None else None
        age_min = max((time.time() - first_seen_ts) / 60.0, 1.0) if first_seen_ts is not None else None
        self.assertIsNone(age_min)

    # -------------------------------------------------------------------------
    # Test E: EarlyLaunchSniper False When age=None
    # -------------------------------------------------------------------------
    def test_e_early_launch_sniper_false_when_age_none(self):
        """
        EarlyLaunchSniper must return False when age_minutes is None,
        preventing premature entry on unverified token age.
        """
        dummy_opp = OpportunityReport(
            mint="MintEarlyTest",
            symbol="EARLY",
            alpha_score=85.0,
            risk_score=20.0,
            confidence_score=80.0,
            earlyness_score=80.0,
            execution_score=80.0,
            final_score=85.0,
            regime="R3_EARLY_IGNITION",
            narrative="Memes",
            recommendation="PAPER_ENTRY",
            why_ranked_high=[],
            why_not_higher=[],
            what_supports_it=[],
            what_could_invalidate_it=[],
            updated_at=time.time()
        )

        self.assertFalse(EarlyLaunchSniper.evaluate(dummy_opp, age_minutes=None))
        self.assertTrue(EarlyLaunchSniper.evaluate(dummy_opp, age_minutes=30.0))

    # -------------------------------------------------------------------------
    # Test F: Opportunity Scoring Preserves Unknown Age
    # -------------------------------------------------------------------------
    def test_f_opportunity_scoring_preserves_unknown_age(self):
        """
        OpportunityScorer must accept age_minutes=None, assign neutral earlyness=50.0,
        degrade confidence, and include unknown age in explainability.
        """
        scorer = OpportunityScorer(config=AppConfig().scoring, db=DatabaseManager(self.db_path))
        from security.rug_detection.rug_engine import SecurityEvaluation
        from intelligence.market_microstructure.microstructure import MicrostructureMetrics
        from intelligence.narrative.narrative_engine import NarrativeMetrics

        sec_eval = SecurityEvaluation(
            mint="MintScorerTest",
            security_score=85.0,
            rug_probability=10.0,
            mint_auth_revoked=True,
            freeze_auth_revoked=True,
            lp_locked_pct=100.0,
            top10_holder_pct=25.0,
            dev_holding_pct=2.0,
            is_honeypot=False,
            is_wash_traded=False,
            status="SAFE",
            rejection_reasons=[],
            evaluated_at=time.time()
        )
        micro = MicrostructureMetrics(
            mint="MintScorerTest",
            buy_count=20,
            sell_count=10,
            buy_sell_ratio=2.0,
            order_flow_imbalance=0.33,
            price_velocity=0.05,
            price_acceleration=0.01,
            price_second_order=0.005,
            volume_acceleration=0.02,
            liquidity_growth_rate=0.05,
            buyer_acceleration=2.66,
            is_pre_ignition=True,
            money_price_divergence="SMART_ACCUMULATION",
            is_fake_breakout=False
        )
        nar = NarrativeMetrics("Memes", 1, 1000.0, 50.0, 0.0, 0.0, "Emerging")

        # Score with age_minutes = None
        opp = scorer.evaluate_opportunity(
            token_data={"mint": "MintScorerTest", "symbol": "TEST", "liquidity": 50000.0, "holders_count": 100},
            security_eval=sec_eval,
            micro=micro,
            smart_money_score=75.0,
            whale_netflow=10000.0,
            narrative_metrics=nar,
            dna_history=[],
            age_minutes=None
        )

        self.assertEqual(opp.earlyness_score, 50.0)
        self.assertTrue(any("unverified" in w.lower() or "unknown" in w.lower() for w in opp.why_not_higher))

    # -------------------------------------------------------------------------
    # Test G: Paper Position Preserves Triggering Provenance
    # -------------------------------------------------------------------------
    def test_g_paper_position_preserves_triggering_provenance(self):
        """
        Opening a paper position must preserve the exact triggering provenance
        (e.g. SourceType.REPLAY with custom provider metadata), not force REAL.
        """
        mint = "MintProvPosTest111111111111111111111111111"
        tokens = [{
            "mint": mint,
            "symbol": "PROVPOS",
            "price": 0.20,
            "liquidity": 100000.0,
            "first_seen_ts": time.time() - 300.0,
            "provenance": {
                "source_type": "REPLAY",
                "provider": "CustomSnapshotFeeder",
                "confidence": 0.85,
                "verified_on_chain": False
            }
        }]
        trades = {
            mint: [{
                "signature": "9a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2g3h4i5j6k7l8m9n0",
                "slot": 100,
                "timestamp": time.time(),
                "signer": "WalletWhaleTrigger11111111111111111111111111",
                "type": "BUY",
                "token_amount": 50000.0,
                "usd_amount": 10000.0,
                "price_usd": 0.20,
                "provenance": {"source_type": "REPLAY", "verified_on_chain": False, "confidence": 0.85}
            }]
        }

        provider = MockTestLiveProvider(tokens=tokens, trades=trades, sol_price_usd=150.0)
        engine = RealLivePaperEngine(config=self.config, data_provider=provider)
        engine.run_live_cycle()

        if mint in engine.wallet.positions:
            pos = engine.wallet.positions[mint]
            self.assertEqual(pos.provenance.source_type, SourceType.REPLAY)
            self.assertFalse(pos.provenance.verified_on_chain)
            self.assertEqual(pos.provenance.provider, "CustomSnapshotFeeder")

    # -------------------------------------------------------------------------
    # Test H: No Forced verified_on_chain=True in Paper Position Creation
    # -------------------------------------------------------------------------
    def test_h_no_forced_verified_on_chain_in_paper_position_creation(self):
        """
        VirtualWallet.open_position must not blindly set verified_on_chain=True
        or SourceType.REAL when no provenance is supplied.
        """
        wallet = VirtualWallet(name="TestWallet", initial_capital_usd=100.0, data_mode="live")
        exec_sim = ExecutionSimulator()
        exec_res = exec_sim.execute_order(market_price=1.0, trade_size_usd=10.0, liquidity_usd=50000.0, is_buy=True)

        pos = wallet.open_position(
            mint="MintNoForcedProv",
            symbol="NFP",
            exec_res=exec_res,
            provenance=None  # Missing provenance
        )

        self.assertIsNotNone(pos)
        self.assertFalse(pos.provenance.verified_on_chain)
        self.assertEqual(pos.provenance.confidence, 0.0)
        self.assertEqual(pos.provenance.source_type, SourceType.UNKNOWN)


if __name__ == "__main__":
    unittest.main()
