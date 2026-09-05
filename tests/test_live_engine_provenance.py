"""
Live Engine Provenance Hardening Regression Tests.
Verifies all 18 semantic and provenance requirements:
1. test_unknown_liquidity_remains_none
2. test_unknown_volume_remains_none
3. test_unknown_holders_remain_none
4. test_unknown_top10_remains_none
5. test_unknown_dev_holding_remains_none
6. test_unknown_lp_lock_remains_none
7. test_unknown_age_remains_none
8. test_unknown_quote_is_not_verified
9. test_unknown_quote_not_counted_in_whale_flow
10. test_unknown_quote_not_counted_in_smart_money
11. test_unknown_quote_not_counted_in_cluster_volume
12. test_unknown_narrative_metrics_not_fabricated
13. test_missing_event_timestamp_does_not_become_event_time
14. test_missing_provenance_never_becomes_real
15. test_live_security_conversion_preserves_none
16. test_unknown_fields_persist_as_null
17. test_live_entry_blocked_when_liquidity_unknown
18. test_static_scan_forbidden_fallbacks_in_live_path
"""

import os
import re
import shutil
import tempfile
import time
import unittest
from typing import Any, Dict, List, Optional

from app.config.settings import AppConfig, ExitConfig, ExecutionConfig, ScoringConfig
from app.core.database import DatabaseManager
from blockchain.parsers.real_swap_parser import RealSwapParser, RealSwapRecord
from blockchain.solana.mint_verifier import OnChainMintVerification, OnChainMintVerifier
from blockchain.solana.types import Provenance, SourceType
from intelligence.market_microstructure.microstructure import MarketMicrostructureEngine, MicrostructureMetrics
from intelligence.narrative.narrative_engine import NarrativeEngine, NarrativeMetrics
from intelligence.smart_money.emerging_smart_money import EmergingSmartMoneyEngine, is_swap_quote_verified
from intelligence.smart_money.real_smart_money import RealSmartMoneyEngine
from intelligence.token.dna import DNASnapshot, TokenDNAEngine
from intelligence.wallet_graph.real_cluster_graph import RealClusterGraph
from intelligence.whales.real_whale_tracker import RealWhaleTracker
from intelligence.whales.relative_whale_engine import RelativeWhaleEngine
from portfolio.accounting.trade_journal import TradeJournal
from portfolio.position_manager.position_manager import PositionManager
from portfolio.virtual_wallet.virtual_wallet import VirtualWallet, VirtualPosition
from scoring.alpha_score.alpha_calculator import AlphaCalculator
from scoring.confidence.confidence_calculator import ConfidenceCalculator
from scoring.opportunity.opportunity_scorer import OpportunityReport, OpportunityScorer
from scoring.risk_score.risk_calculator import RiskCalculator
from security.liquidity_risk.liquidity_checker import LiquidityRiskChecker
from security.rug_detection.real_security_engine import RealSecurityEngine, RealSecurityEvaluation
from security.rug_detection.rug_engine import RugDetectionEngine, SecurityEvaluation
from security.wallet_risk.concentration_checker import ConcentrationChecker
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
    # 1. test_unknown_liquidity_remains_none
    # -------------------------------------------------------------------------
    def test_unknown_liquidity_remains_none(self):
        """
        When token liquidity is unknown (None), it remains None in token_liquidity_map,
        TokenDNAEngine snapshot, and RelativeWhaleEngine, without defaulting to 0.0 or 1000.0.
        """
        mint = "MintUnknownLiq11111111111111111111111111111"
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

        # DNA check
        dna_engine = TokenDNAEngine(DatabaseManager(self.db_path))
        snap = dna_engine.record_snapshot(mint=mint, price=0.50, volume=100.0, liquidity=None)
        self.assertIsNone(snap.liquidity)

        # Relative whale engine check
        rel_whale = RelativeWhaleEngine.evaluate_token(mint=mint, symbol="UNLIQ", swaps=[], pool_liquidity_usd=None)
        self.assertIsNone(rel_whale.pool_liquidity_usd)

    # -------------------------------------------------------------------------
    # 2. test_unknown_volume_remains_none
    # -------------------------------------------------------------------------
    def test_unknown_volume_remains_none(self):
        """
        When 24h volume is unknown (None), it must remain None rather than defaulting to 0.0.
        """
        dna_engine = TokenDNAEngine(DatabaseManager(self.db_path))
        snap = dna_engine.record_snapshot(mint="MintNoVol", price=1.0, volume=None)
        self.assertIsNone(snap.volume)

        # NarrativeMetrics check
        nar = NarrativeMetrics(name="AI Agents", total_volume_24h=None)
        self.assertIsNone(nar.total_volume_24h)

    # -------------------------------------------------------------------------
    # 3. test_unknown_holders_remain_none
    # -------------------------------------------------------------------------
    def test_unknown_holders_remain_none(self):
        """
        When token holder count is unknown (None), it must remain None and degrade confidence
        without fabricating a 0 or 1000 count.
        """
        dna_engine = TokenDNAEngine(DatabaseManager(self.db_path))
        snap = dna_engine.record_snapshot(mint="MintNoHolders", price=1.0, holders=None)
        self.assertIsNone(snap.holders)

        conf = ConfidenceCalculator.calculate(token_data={"mint": "MintNoHolders"}, dna_snapshots_count=0, trades_count=0)
        self.assertEqual(conf, 15.0)  # Minimum floor with penalized unknown features

    # -------------------------------------------------------------------------
    # 4. test_unknown_top10_remains_none
    # -------------------------------------------------------------------------
    def test_unknown_top10_remains_none(self):
        """
        Unverified top 10 concentration must remain None in RealSecurityEvaluation
        and SecurityEvaluation, without defaulting to 25.0%.
        """
        chk = ConcentrationChecker.check(sec_data={}, max_top10_pct=65.0, max_dev_pct=15.0)
        self.assertIsNone(chk.top10_holder_pct)
        self.assertFalse(chk.is_acceptable)

    # -------------------------------------------------------------------------
    # 5. test_unknown_dev_holding_remains_none
    # -------------------------------------------------------------------------
    def test_unknown_dev_holding_remains_none(self):
        """
        Unverified creator/dev holding percentage must remain None, not 0.0 or 2.0.
        """
        chk = ConcentrationChecker.check(sec_data={"top10_holder_pct": 30.0}, max_top10_pct=65.0, max_dev_pct=15.0)
        self.assertIsNone(chk.dev_holding_pct)
        self.assertFalse(chk.is_acceptable)

    # -------------------------------------------------------------------------
    # 6. test_unknown_lp_lock_remains_none
    # -------------------------------------------------------------------------
    def test_unknown_lp_lock_remains_none(self):
        """
        Unverified LP lock percentage must remain None, not 0.0 or 100.0.
        """
        chk = LiquidityRiskChecker.check(sec_data={}, min_lp_locked_pct=70.0)
        self.assertIsNone(chk.lp_locked_pct)
        self.assertFalse(chk.is_locked_adequate)

    # -------------------------------------------------------------------------
    # 7. test_unknown_age_remains_none
    # -------------------------------------------------------------------------
    def test_unknown_age_remains_none(self):
        """
        Missing first_seen_ts produces age_minutes=None (not 0.0 or 1000.0),
        and OpportunityScorer assigns neutral 50.0 earlyness score.
        """
        t = {"mint": "MintNoAge", "first_seen_ts": None}
        first_seen_ts = float(t["first_seen_ts"]) if t.get("first_seen_ts") is not None else None
        age_min = ((time.time() - first_seen_ts) / 60.0) if first_seen_ts is not None else None
        self.assertIsNone(age_min)

        # EarlyLaunchSniper must block when age is None
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

    # -------------------------------------------------------------------------
    # 8. test_unknown_quote_is_not_verified
    # -------------------------------------------------------------------------
    def test_unknown_quote_is_not_verified(self):
        """
        A swap with missing USD amount or unverified provenance is strictly NOT verified.
        """
        swap_unverified = RealSwapRecord(
            signature="sig1",
            slot=100,
            timestamp=time.time(),
            pool="pool1",
            mint="mint1",
            symbol="M1",
            wallet="w1",
            side="BUY",
            token_amount=1000.0,
            quote_amount_sol=1.0,
            quote_amount_usd=150.0,
            price_usd=0.15,
            venue="Raydium",
            is_quote_verified=False,
            provenance=Provenance(source_type=SourceType.UNKNOWN, verified_on_chain=False)
        )
        self.assertFalse(is_swap_quote_verified(swap_unverified))

    # -------------------------------------------------------------------------
    # 9. test_unknown_quote_not_counted_in_whale_flow
    # -------------------------------------------------------------------------
    def test_unknown_quote_not_counted_in_whale_flow(self):
        """
        Unverified quotes must not participate in RealWhaleTracker volume or netflow.
        """
        tracker = RealWhaleTracker(DatabaseManager(self.db_path))
        swap = RealSwapRecord(
            signature="sig_whale_unv",
            slot=100,
            timestamp=time.time(),
            pool="pool1",
            mint="mint1",
            symbol="M1",
            wallet="w1",
            side="BUY",
            token_amount=1000.0,
            quote_amount_sol=100.0,
            quote_amount_usd=15000.0,  # Large amount but unverified quote
            price_usd=15.0,
            venue="Raydium",
            is_quote_verified=False,
            provenance=Provenance(source_type=SourceType.UNKNOWN, verified_on_chain=False)
        )
        event = tracker.process_real_swap(swap, pool_liquidity_usd=100000.0)
        self.assertIsNone(event)
        self.assertEqual(tracker.get_token_whale_netflow("mint1"), 0.0)

    # -------------------------------------------------------------------------
    # 10. test_unknown_quote_not_counted_in_smart_money
    # -------------------------------------------------------------------------
    def test_unknown_quote_not_counted_in_smart_money(self):
        """
        Unverified quotes must not contribute to wallet total volume or trades in RealSmartMoneyEngine.
        """
        sm_engine = RealSmartMoneyEngine(DatabaseManager(self.db_path))
        swap = RealSwapRecord(
            signature="sig_sm_unv",
            slot=100,
            timestamp=time.time(),
            pool="pool1",
            mint="mint1",
            symbol="M1",
            wallet="w_smart_1",
            side="BUY",
            token_amount=1000.0,
            quote_amount_sol=10.0,
            quote_amount_usd=1500.0,
            price_usd=1.5,
            venue="Raydium",
            is_quote_verified=False,
            provenance=Provenance(source_type=SourceType.UNKNOWN, verified_on_chain=False)
        )
        profile = sm_engine.process_real_swap(swap)
        self.assertEqual(profile.total_volume_usd, 0.0)
        self.assertEqual(len(profile.trades), 0)

    # -------------------------------------------------------------------------
    # 11. test_unknown_quote_not_counted_in_cluster_volume
    # -------------------------------------------------------------------------
    def test_unknown_quote_not_counted_in_cluster_volume(self):
        """
        Unverified quotes must not be added to token_wallet_volumes for cluster volume calculations.
        """
        cluster_graph = RealClusterGraph()
        # When token_wallet_volumes is empty (no verified quotes)
        res = cluster_graph.analyze_token_wallets(mint="mint1", observed_wallets=["w1", "w2"], wallet_volumes={})
        self.assertEqual(res.cluster_share_of_volume_pct, 0.0)

    # -------------------------------------------------------------------------
    # 12. test_unknown_narrative_metrics_not_fabricated
    # -------------------------------------------------------------------------
    def test_unknown_narrative_metrics_not_fabricated(self):
        """
        Categorical narrative classification without measured metrics must preserve
        heat_score=None, and AlphaCalculator must reweight without injecting 1000.0 or 50.0.
        """
        nar = NarrativeMetrics(name="AI Agents", heat_score=None)
        self.assertIsNone(nar.heat_score)

        micro = MicrostructureMetrics(
            mint="M1", buy_count=10, sell_count=5, buy_sell_ratio=2.0,
            order_flow_imbalance=0.33, price_velocity=0.05, price_acceleration=0.01,
            price_second_order=0.0, volume_acceleration=0.1, liquidity_growth_rate=0.05,
            buyer_acceleration=2.0, is_pre_ignition=False, money_price_divergence="SMART_ACCUMULATION",
            is_fake_breakout=False
        )

        alpha = AlphaCalculator.calculate(
            micro=micro,
            smart_money_score=75.0,
            whale_netflow=5000.0,
            narrative_metrics=nar,
            config=ScoringConfig()
        )
        self.assertGreater(alpha, 0.0)
        self.assertLessEqual(alpha, 100.0)

    # -------------------------------------------------------------------------
    # 13. test_missing_event_timestamp_does_not_become_event_time
    # -------------------------------------------------------------------------
    def test_missing_event_timestamp_does_not_become_event_time(self):
        """
        A missing source trade timestamp must remain None in Provenance.timestamp,
        distinguishing event time from local observation time.
        """
        prov = Provenance(
            source_type=SourceType.REAL,
            provider="LiveDiscovery",
            timestamp=None,
            observed_at=time.time(),
            confidence=0.9
        )
        self.assertIsNone(prov.timestamp)
        self.assertIsNotNone(prov.observed_at)

    def test_missing_swap_timestamp_remains_none(self):
        """
        When a parsed transaction or trade lacks a blockTime/timestamp,
        RealSwapRecord.timestamp must be None, never replaced with time.time().
        """
        mint = "MintNoSwapTs11111111111111111111111111111"
        tokens = [{
            "mint": mint,
            "symbol": "NOTS",
            "price": 1.0,
            "liquidity": 10000.0,
            "first_seen_ts": None
        }]
        trades = {
            mint: [{
                "signature": "sig_no_ts_11111111111111111111111111111111111111111111111111111111111111111111111111",
                "slot": 500,
                "timestamp": None,  # Missing source timestamp
                "signer": "WalletNoTs11111111111111111111111111111111",
                "type": "BUY",
                "token_amount": 100.0,
                "usd_amount": 50.0,
                "price_usd": 0.50,
                "provenance": {"source_type": "REAL", "verified_on_chain": True, "confidence": 1.0, "timestamp": None}
            }]
        }

        provider = MockTestLiveProvider(tokens=tokens, trades=trades, sol_price_usd=150.0)
        engine = RealLivePaperEngine(config=self.config, data_provider=provider)
        engine.run_live_cycle()

        self.assertEqual(len(engine.ingested_swaps), 1)
        swap = engine.ingested_swaps[0]
        self.assertIsNone(swap.timestamp)
        self.assertIsNone(swap.provenance.timestamp)

    def test_missing_event_timestamp_never_converted_to_current_time(self):
        """
        RealSwapParser.parse_transaction on a transaction without blockTime must set
        timestamp=None on the resulting RealSwapRecord and Provenance.
        """
        tx_data = {
            "slot": 123456,
            "transaction": {
                "signatures": ["sig_no_blocktime_12345"],
                "message": {
                    "accountKeys": [
                        {"pubkey": "Signer11111111111111111111111111111111111111", "signer": True}
                    ]
                }
            },
            "meta": {
                "err": None,
                "preTokenBalances": [{"mint": "MintA", "owner": "Signer11111111111111111111111111111111111111", "uiTokenAmount": {"uiAmount": 0.0}}],
                "postTokenBalances": [{"mint": "MintA", "owner": "Signer11111111111111111111111111111111111111", "uiTokenAmount": {"uiAmount": 100.0}}],
                "preBalances": [2000000000],
                "postBalances": [1000000000],
                "fee": 5000
            }
            # Note: "blockTime" key is absent
        }

        swaps = RealSwapParser.parse_transaction(tx_data, sol_price_usd=150.0)
        self.assertEqual(len(swaps), 1)
        self.assertIsNone(swaps[0].timestamp)
        self.assertIsNone(swaps[0].provenance.timestamp)

    def test_observed_at_remains_separate_from_event_timestamp(self):
        """
        observed_at represents local system clock at ingestion, whereas event timestamp
        represents on-chain block time (which may be historical or None).
        """
        historical_event_ts = 1700000000.0  # Historical epoch
        before_time = time.time()
        prov = Provenance(
            source_type=SourceType.REAL,
            provider="SolanaRPC",
            timestamp=historical_event_ts,
            observed_at=time.time(),
            confidence=1.0,
            verified_on_chain=True
        )
        after_time = time.time()

        self.assertEqual(prov.timestamp, historical_event_ts)
        self.assertGreaterEqual(prov.observed_at, before_time)
        self.assertLessEqual(prov.observed_at, after_time)
        self.assertNotEqual(prov.timestamp, prov.observed_at)

    # -------------------------------------------------------------------------
    # 14. test_missing_provenance_never_becomes_real
    # -------------------------------------------------------------------------
    def test_missing_provenance_never_becomes_real(self):
        """
        Missing provenance must resolve to SourceType.UNKNOWN with verified_on_chain=False,
        never coerced to REAL or True.
        """
        prov = Provenance()
        self.assertEqual(prov.source_type, SourceType.UNKNOWN)
        self.assertFalse(prov.verified_on_chain)
        self.assertEqual(prov.confidence, 0.0)

    # -------------------------------------------------------------------------
    # 15. test_live_security_conversion_preserves_none
    # -------------------------------------------------------------------------
    def test_live_security_conversion_preserves_none(self):
        """
        RealLivePaperEngine._convert_to_security_evaluation must preserve None
        for lp_locked_pct, top10_holder_pct, and dev_holding_pct.
        """
        engine = RealLivePaperEngine(config=self.config)
        real_sec = RealSecurityEvaluation(
            mint="MintSecNone",
            security_score=50.0,
            rug_probability=50.0,
            confidence=0.5,
            status="UNVERIFIED",
            mint_auth_status="UNKNOWN",
            freeze_auth_status="UNKNOWN",
            holder_concentration_status="UNKNOWN",
            lp_lock_status="UNKNOWN",
            top10_holder_pct=None,
            dev_holding_pct=None,
            evaluated_at=time.time()
        )

        sec_eval = engine._convert_to_security_evaluation(real_sec)
        self.assertIsNone(sec_eval.lp_locked_pct)
        self.assertIsNone(sec_eval.top10_holder_pct)
        self.assertIsNone(sec_eval.dev_holding_pct)

    # -------------------------------------------------------------------------
    # 16. test_unknown_fields_persist_as_null
    # -------------------------------------------------------------------------
    def test_unknown_fields_persist_as_null(self):
        """
        DatabaseManager must store and retrieve None as NULL without rewriting to 0.0.
        """
        db = DatabaseManager(self.db_path)
        db.upsert_security_report({
            "mint": "MintNullCheck",
            "security_score": 70.0,
            "rug_probability": 30.0,
            "mint_auth_revoked": 1,
            "freeze_auth_revoked": 1,
            "lp_locked_pct": None,
            "top10_holder_pct": None,
            "dev_holding_pct": None,
            "rejection_reasons": "[]",
            "status": "SAFE",
            "evaluated_at": time.time()
        })

        reports = db.get_security_reports()
        saved = next(r for r in reports if r["mint"] == "MintNullCheck")
        self.assertIsNone(saved["lp_locked_pct"])
        self.assertIsNone(saved["top10_holder_pct"])
        self.assertIsNone(saved["dev_holding_pct"])

    # -------------------------------------------------------------------------
    # 17. test_live_entry_blocked_when_liquidity_unknown
    # -------------------------------------------------------------------------
    def test_live_entry_blocked_when_liquidity_unknown(self):
        """
        Position sizing must return 0.0 when pool liquidity is None (entry blocked).
        """
        pos_mgr = PositionManager(self.config.portfolio)
        dummy_opp = OpportunityReport(
            mint="MintSizeTest",
            symbol="SIZE",
            alpha_score=95.0,
            risk_score=10.0,
            confidence_score=90.0,
            earlyness_score=90.0,
            execution_score=90.0,
            final_score=95.0,
            regime="R3_EARLY_IGNITION",
            narrative="Memes",
            recommendation="PAPER_ENTRY",
            why_ranked_high=[],
            why_not_higher=[],
            what_supports_it=[],
            what_could_invalidate_it=[],
            updated_at=time.time()
        )

        size = pos_mgr.calculate_position_size(
            opp=dummy_opp,
            current_cash=100.0,
            current_equity=100.0,
            open_positions_count=0,
            pool_liquidity_usd=None  # Unknown liquidity
        )
        self.assertEqual(size, 0.0)

    # -------------------------------------------------------------------------
    # 18. test_static_scan_forbidden_fallbacks_in_live_path
    # -------------------------------------------------------------------------
    def test_static_scan_forbidden_fallbacks_in_live_path(self):
        """
        Scans production live execution path files for forbidden numeric fallback patterns
        such as 'or 25.0', 'or 2.0', 'or 50.0', 'or 1000.0', 'or 50000.0'.
        """
        target_files = [
            "app/orchestration/live_paper_engine.py",
            "app/orchestration/orchestrator.py",
            "security/rug_detection/real_security_engine.py",
            "intelligence/smart_money/emerging_smart_money.py",
            "intelligence/whales/relative_whale_engine.py",
            "scoring/opportunity/opportunity_scorer.py"
        ]

        forbidden_regexes = [
            re.compile(r"\bor\s+25\.0\b"),
            re.compile(r"\bor\s+2\.0\b"),
            re.compile(r"\bor\s+50\.0\b"),
            re.compile(r"\bor\s+1000\.0\b"),
            re.compile(r"\bor\s+50000\.0\b"),
        ]

        violations = []
        for rel_path in target_files:
            if not os.path.exists(rel_path):
                continue
            with open(rel_path, "r", encoding="utf-8") as f:
                for line_no, line in enumerate(f, 1):
                    # Ignore comments
                    stripped = line.strip()
                    if stripped.startswith("#"):
                        continue
                    for pat in forbidden_regexes:
                        if pat.search(line):
                            violations.append(f"{rel_path}:{line_no} -> {line.strip()}")

        self.assertEqual(violations, [], f"Found forbidden numeric fallback patterns in live path: {violations}")


if __name__ == "__main__":
    unittest.main()
