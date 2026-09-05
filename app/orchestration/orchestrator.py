"""
Master Orchestrator for Meme Alpha Hunter.
Strict Provenance: DISCOVER -> FILTER -> UNDERSTAND -> SCORE -> RANK -> SIMULATE -> MONITOR -> LEARN
"""

import json
import logging
import time
from typing import Any, Dict, List, Optional

from ai_expert.thesis_generator import AIExpertThesisGenerator, StructuredAIThesis
from alerts.telegram.bot_engine import TelegramBotEngine
from app.config.settings import AppConfig, load_config
from app.core.database import DatabaseManager
from app.core.health_monitor import HealthMonitor, HealthStatus
from blockchain.solana.types import Provenance, SourceType
from data.ingestion.live_market_feeder import LiveMarketFeeder
from data.ingestion.mock_feeder import MarketFeeder
from data.ingestion.provider_base import BaseDataProvider
from discovery.opportunity_discovery.queue import OpportunityQueue
from discovery.token_discovery.token_scanner import DiscoveredToken, TokenDiscoveryScanner
from intelligence.creator.creator_tracker import CreatorTracker
from intelligence.market_microstructure.microstructure import MarketMicrostructureEngine, MicrostructureMetrics
from intelligence.narrative.narrative_engine import NarrativeEngine, NarrativeMetrics
from intelligence.smart_money.smart_engine import SmartMoneyEngine
from intelligence.token.dna import TokenDNAEngine
from intelligence.wallet_graph.cluster_graph import WalletClusterGraph
from intelligence.whales.whale_radar import WhaleRadar
from ml.features.feature_extractor import FeatureExtractor
from ml.models.baseline_model import ProbabilisticMLModel, ProbabilityDistribution
from portfolio.accounting.multi_strategy import MultiStrategySuite
from portfolio.accounting.trade_journal import TradeJournal
from portfolio.pnl.pnl_calculator import PerformanceMetrics, PnLCalculator
from portfolio.position_manager.position_manager import PositionManager
from portfolio.risk_manager.risk_manager import PortfolioRiskManager
from portfolio.virtual_wallet.virtual_wallet import VirtualWallet
from scoring.opportunity.opportunity_scorer import OpportunityReport, OpportunityScorer
from security.rug_detection.rug_engine import RugDetectionEngine, SecurityEvaluation
from simulation.execution.execution_engine import ExecutionSimulator
from sniper.early_launch.early_launch_sniper import EarlyLaunchSniper
from sniper.execution.anti_sniper import AntiSniperDefense
from sniper.execution.chase_detector import ChaseDetector
from sniper.execution.exit_engine import DynamicExitEngine
from sniper.execution.state_machine import SniperStage, SniperStateMachine
from sniper.hybrid.hybrid_sniper import HybridSniper
from sniper.momentum.momentum_sniper import MomentumSniper
from sniper.smart_money.smart_money_sniper import SmartMoneySniper
from sniper.whale.whale_sniper import WhaleSniper

logger = logging.getLogger("meme_alpha_hunter.orchestrator")


class MemeAlphaHunterOrchestrator:
    def __init__(self, config: Optional[AppConfig] = None, data_provider: Optional[BaseDataProvider] = None):
        self.config = config or load_config()
        self.db = DatabaseManager(self.config.db_path)
        self.health = HealthMonitor(self.db)
        self.data_mode = self.config.data_mode.lower()

        if data_provider:
            self.provider = data_provider
        elif self.data_mode == "mock":
            self.provider = MarketFeeder()
        else:
            self.provider = LiveMarketFeeder(data_mode=self.data_mode)

        # Core Engines
        self.token_scanner = TokenDiscoveryScanner(self.provider, self.config.discovery, self.db)
        self.dna_engine = TokenDNAEngine(self.db)
        self.security_engine = RugDetectionEngine(self.config.security, self.db)
        self.whale_radar = WhaleRadar(self.db)
        self.smart_money_engine = SmartMoneyEngine(self.db)
        self.cluster_graph = WalletClusterGraph()
        self.creator_tracker = CreatorTracker()
        self.narrative_engine = NarrativeEngine()
        self.scorer = OpportunityScorer(self.config.scoring, self.db)
        self.state_machine = SniperStateMachine()
        self.exit_engine = DynamicExitEngine(self.config.exit_rules)
        self.exec_simulator = ExecutionSimulator(self.config.execution)

        # Portfolio & Risk with strict accounting
        self.wallet = VirtualWallet(
            name="Main_Virtual_Wallet",
            initial_capital_usd=self.config.portfolio.initial_capital_usd,
            data_mode=self.data_mode
        )
        self.position_manager = PositionManager(self.config.portfolio)
        self.risk_manager = PortfolioRiskManager(self.config.portfolio)
        self.journal = TradeJournal(self.db)
        self.multi_strategy = MultiStrategySuite(initial_capital_each=self.config.portfolio.initial_capital_usd)

        # Alerts & Queue
        self.telegram = TelegramBotEngine(self.config.telegram)
        self.opp_queue = OpportunityQueue()

        # In-memory tracking
        self.last_scanned_tokens: List[DiscoveredToken] = []
        self.rejected_tokens: List[Dict[str, Any]] = []
        self.top_opportunities: List[OpportunityReport] = []
        self.ai_theses: Dict[str, StructuredAIThesis] = {}
        self.evaluated_securities: Dict[str, SecurityEvaluation] = {}
        self.accounting_assertion_passed = True
        self.last_accounting_status = "INITIALIZED"

    def run_pipeline_cycle(self) -> Dict[str, Any]:
        """
        Executes one complete end-to-end pipeline cycle:
        DISCOVER -> FILTER -> UNDERSTAND -> SCORE -> RANK -> SIMULATE -> MONITOR -> LEARN
        """
        logger.info(f"=== Starting Pipeline Cycle [DATA_MODE={self.data_mode.upper()}] ===")
        cycle_start_time = time.time()

        try:
            # 1. DISCOVERY
            discovered = self.token_scanner.scan(limit=30)
            self.last_scanned_tokens = discovered

            if not discovered:
                if self.data_mode == "live":
                    msg = "LIVE DATA UNAVAILABLE: No response from public Solana RPC/DEX endpoints."
                    logger.warning(msg)
                    self.health.record_status("DISCOVERY", HealthStatus.DEGRADED, msg)
                else:
                    self.health.record_status("DISCOVERY", HealthStatus.HEALTHY, "0 tokens discovered")
                # Maintain open positions update if any
                return self._finalize_cycle_and_validate(cycle_start_time, discovered)

            self.health.record_status("DISCOVERY", HealthStatus.HEALTHY, f"Scanned {len(discovered)} tokens")

            # Collect narrative overview
            raw_token_dicts = [self.provider.get_token_market_data(t.mint) or {} for t in discovered if t.mint]
            narratives_map = self.narrative_engine.update_narratives(raw_token_dicts)

            current_opps: List[OpportunityReport] = []

            for token in discovered:
                mint = token.mint
                token_data = self.provider.get_token_market_data(mint) or {}

                # 2. FILTER & SECURITY (Hard reject filters)
                sec_data = self.provider.get_token_security_data(mint) or {}
                security_eval = self.security_engine.evaluate(mint, sec_data)
                self.evaluated_securities[mint] = security_eval

                if not token.is_qualified or security_eval.status == "HARD_REJECT":
                    rejection_reasons = []
                    if token.rejection_reason:
                        rejection_reasons.append(token.rejection_reason)
                    rejection_reasons.extend(security_eval.rejection_reasons)

                    self.rejected_tokens.append({
                        "mint": mint,
                        "symbol": token.symbol,
                        "security_score": security_eval.security_score,
                        "rug_probability": security_eval.rug_probability,
                        "reasons": "; ".join(rejection_reasons),
                        "source_type": token.provenance.source_type.value if hasattr(token, "provenance") else "UNKNOWN"
                    })
                    self.state_machine.transition(mint, SniperStage.SX_KILL)
                    continue

                # 3. UNDERSTAND (Intelligence Layer)
                trades = self.provider.get_recent_trades(mint, limit=30)
                for tr in trades:
                    self.whale_radar.process_trade(tr, token.liquidity)

                seed_smart_score = float(token_data.get("smart_money_score", 75.0))
                smart_signal = self.smart_money_engine.evaluate_token_smart_money(mint, trades, base_smart_score=seed_smart_score)
                whale_flow = self.whale_radar.get_token_whale_netflow(mint)

                # DNA Record
                dna_hist = self.dna_engine.get_history(mint)
                self.dna_engine.record_snapshot(
                    mint=mint,
                    price=token.price,
                    volume=token.volume_24h,
                    liquidity=token.liquidity,
                    holders=token.holders_count,
                    smart_money_flow=smart_signal.netflow_usd,
                    whale_netflow=whale_flow
                )

                # Microstructure & Acceleration
                micro = MarketMicrostructureEngine.compute(
                    mint=mint,
                    token_data=token_data,
                    dna_history=dna_hist,
                    smart_money_score=smart_signal.smart_money_score,
                    whale_netflow=whale_flow
                )

                # Narrative
                nar_name = self.narrative_engine.classify_token_narrative(token.symbol, token.name)
                nar_metrics = narratives_map.get(nar_name, NarrativeMetrics(nar_name, 1, 1000.0, 50.0, 0.0, 0.0, "Emerging"))

                # 4. SCORE & RANK
                age_min = (time.time() - token.first_seen_ts) / 60.0
                opp_report = self.scorer.evaluate_opportunity(
                    token_data=token_data,
                    security_eval=security_eval,
                    micro=micro,
                    smart_money_score=smart_signal.smart_money_score,
                    whale_netflow=whale_flow,
                    narrative_metrics=nar_metrics,
                    dna_history=dna_hist,
                    age_minutes=age_min
                )
                current_opps.append(opp_report)

                # ML Probability & AI Thesis
                features = FeatureExtractor.extract_vector(
                    token_data=token_data,
                    micro=micro,
                    smart_money_score=smart_signal.smart_money_score,
                    whale_netflow=whale_flow,
                    security_score=security_eval.security_score,
                    rug_probability=security_eval.rug_probability,
                    dna_history=dna_hist
                )
                probs = ProbabilisticMLModel.predict_probabilities(features)
                thesis = AIExpertThesisGenerator.generate(
                    opp=opp_report,
                    probs=probs,
                    smart_money_score=smart_signal.smart_money_score,
                    whale_netflow=whale_flow
                )
                self.ai_theses[mint] = thesis

                # 5. SNIPER & EXECUTION EVALUATION
                chase_verdict = ChaseDetector.evaluate_entry(
                    price_velocity=micro.price_velocity,
                    price_acceleration=micro.price_acceleration,
                    regime=opp_report.regime,
                    alpha_score=opp_report.alpha_score
                )

                # Sniper Modes Checks
                mode_a = EarlyLaunchSniper.evaluate(opp_report, age_min)
                mode_b = SmartMoneySniper.evaluate(opp_report, smart_signal.smart_money_score, smart_signal.netflow_usd)
                mode_c = WhaleSniper.evaluate(opp_report, whale_flow)
                mode_d = MomentumSniper.evaluate(opp_report, micro.is_pre_ignition, micro.price_velocity)
                mode_e = HybridSniper.evaluate(opp_report, smart_signal.smart_money_score, whale_flow, micro.is_pre_ignition)

                should_snipe = (mode_a or mode_b or mode_c or mode_d or mode_e) and chase_verdict.is_safe_entry

                # STRICT PROVENANCE CHECK: If in live mode and data is not REAL, abort entry
                if self.data_mode == "live" and getattr(token.provenance, "source_type", None) != SourceType.REAL:
                    should_snipe = False

                if should_snipe and mint not in self.wallet.positions:
                    # Risk circuit check
                    risk_check = self.risk_manager.evaluate_risk(
                        current_equity=self.wallet.equity_usd,
                        current_cash=self.wallet.cash_usd,
                        max_drawdown_pct=self.wallet.max_drawdown_pct
                    )

                    if risk_check.allowed_to_trade:
                        target_size = self.position_manager.calculate_position_size(
                            opp=opp_report,
                            current_cash=self.wallet.cash_usd,
                            current_equity=self.wallet.equity_usd,
                            open_positions_count=len(self.wallet.positions),
                            pool_liquidity_usd=token.liquidity
                        )

                        if target_size > 0.0:
                            # 6. SIMULATE PAPER ENTRY
                            exec_res = self.exec_simulator.execute_order(
                                market_price=token.price,
                                trade_size_usd=target_size,
                                liquidity_usd=token.liquidity,
                                is_buy=True
                            )

                            pos = self.wallet.open_position(
                                mint=mint,
                                symbol=token.symbol,
                                exec_res=exec_res,
                                alpha_score=opp_report.alpha_score,
                                risk_score=opp_report.risk_score,
                                regime=opp_report.regime,
                                provenance=token.provenance
                            )

                            if pos:
                                self.state_machine.transition(mint, SniperStage.S4_PAPER_EXECUTION)
                                logger.info(f"🎯 [PAPER BUY] {token.symbol} @ ${exec_res.executed_price:.6f} | Size: ${exec_res.filled_size_usd:.2f} | Alpha: {opp_report.alpha_score}")
                                self.telegram.alert_trade_execution("ENTRY", token.symbol, exec_res.executed_price, exec_res.filled_size_usd)

            current_opps.sort(key=lambda x: x.final_score, reverse=True)
            self.top_opportunities = current_opps

            return self._finalize_cycle_and_validate(cycle_start_time, discovered)

        except Exception as e:
            logger.error(f"Critical error during pipeline cycle: {e}", exc_info=True)
            self.health.record_status("SCORING", HealthStatus.FAILED, str(e))
            return {"error": str(e)}

    def _finalize_cycle_and_validate(self, cycle_start_time: float, discovered: List[DiscoveredToken]) -> Dict[str, Any]:
        """
        Monitors open positions using dynamic real metrics (NO hardcoded constants),
        triggers exits, checks accounting invariants, and logs records.
        """
        # Price map for current tokens
        price_map = {t.mint: t.price for t in discovered}
        self.wallet.update_prices(price_map)

        # 7. DYNAMIC MONITORING & EXITS
        mints_to_close = []
        for mint, pos in list(self.wallet.positions.items()):
            curr_price = price_map.get(mint, pos.current_price)

            # Fetch dynamic real token market data (Zero hardcoded 50000 fallback)
            live_token_data = self.provider.get_token_market_data(mint) or {}
            raw_liq = live_token_data.get("liquidity")
            live_liq = float(raw_liq) if raw_liq is not None else None

            # Fetch dynamic real trades & smart money / whale metrics
            recent_trades = self.provider.get_recent_trades(mint, limit=30)
            live_smart = self.smart_money_engine.evaluate_token_smart_money(mint, recent_trades)
            live_whale_flow = self.whale_radar.get_token_whale_netflow(mint)

            exit_verdict = self.exit_engine.evaluate_position(
                entry_price=pos.entry_price,
                current_price=curr_price,
                peak_price=pos.peak_price,
                entry_time=pos.entry_time,
                current_time=time.time(),
                smart_money_score=live_smart.smart_money_score,
                whale_netflow=live_whale_flow,
                regime=pos.regime,
                liquidity_usd=live_liq
            )

            if exit_verdict.should_exit:
                mints_to_close.append((mint, pos, exit_verdict, live_liq))

        # Process Dynamic Exits
        for mint, pos, verdict, liq_usd in mints_to_close:
            exit_exec = self.exec_simulator.execute_order(
                market_price=pos.current_price,
                trade_size_usd=pos.current_gross_value_usd * verdict.sell_ratio,
                liquidity_usd=liq_usd,
                is_buy=False
            )

            closed_pos = self.wallet.close_position(mint, exit_exec, exit_reason=verdict.exit_reason)
            if closed_pos:
                self.state_machine.transition(mint, SniperStage.S7_EXIT)
                # Trade net realized PnL = Net proceeds - Capital invested - Entry fees
                pnl_usd = exit_exec.filled_size_usd - exit_exec.fees.total_fee_usd - pos.size_usd - pos.entry_fees_paid_usd

                # Register trade in journal with provenance
                self.journal.record_completed_trade(
                    strategy_name=self.wallet.name,
                    mint=mint,
                    symbol=pos.symbol,
                    entry_time=pos.entry_time,
                    entry_price=pos.entry_price,
                    size_usd=pos.size_usd,
                    simulated_fill_qty=pos.tokens_amount,
                    liquidity_usd=liq_usd,
                    slippage_usd=pos.entry_slippage_paid_usd + exit_exec.slippage.slippage_usd,
                    fee_usd=pos.entry_fees_paid_usd + exit_exec.fees.total_fee_usd,
                    exit_time=time.time(),
                    exit_price=exit_exec.executed_price,
                    exit_reason=verdict.exit_reason,
                    realized_pnl=pnl_usd,
                    peak_price=pos.peak_price,
                    lowest_price=pos.lowest_price,
                    alpha_score=pos.alpha_score,
                    risk_score=pos.risk_score,
                    regime=pos.regime
                )

                self.risk_manager.register_trade_outcome(is_win=(pnl_usd > 0))
                logger.info(f"🏁 [PAPER SELL] {pos.symbol} @ ${exit_exec.executed_price:.6f} | PnL: ${pnl_usd:+.2f} | Reason: {verdict.exit_reason}")
                self.telegram.alert_trade_execution("EXIT", pos.symbol, exit_exec.executed_price, pos.size_usd, pnl_usd)

        # 8. VALIDATE ACCOUNTING INVARIANTS
        is_valid, inv_msg = self.wallet.validate_accounting_invariants()
        self.accounting_assertion_passed = is_valid
        self.last_accounting_status = inv_msg

        if not is_valid:
            logger.critical(f"ACCOUNTING ASSERTION FAILED: {inv_msg}")
            self.health.record_status("PAPER_TRADING", HealthStatus.FAILED, inv_msg)
        else:
            summary = self.wallet.get_summary()
            self.health.record_status("PAPER_TRADING", HealthStatus.HEALTHY, f"Equity: ${summary['equity']:.2f} (Invariants Valid)")
            self.db.record_portfolio_snapshot({
                "timestamp": time.time(),
                "strategy_name": self.wallet.name,
                "cash_balance": summary["cash"],
                "equity": summary["equity"],
                "open_positions_val": summary["open_positions_val"],
                "realized_pnl": summary["realized_pnl"],
                "unrealized_pnl": summary["unrealized_pnl"],
                "total_fees": summary["total_fees"],
                "total_slippage": summary["total_slippage"],
                "drawdown_pct": summary["max_drawdown_pct"]
            })

        cycle_duration = time.time() - cycle_start_time
        summary = self.wallet.get_summary()
        logger.info(f"=== Pipeline Cycle Finished in {cycle_duration:.2f}s | Active Positions: {len(self.wallet.positions)} | Equity: ${summary['equity']:.2f} | Invariants: {inv_msg} ===")

        return {
            "cycle_duration_sec": cycle_duration,
            "discovered_count": len(discovered),
            "rejected_count": len(self.rejected_tokens),
            "top_opportunities": self.top_opportunities[:5],
            "portfolio_summary": summary,
            "accounting_valid": is_valid,
            "accounting_status": inv_msg
        }
