"""
Composite Opportunity Scorer & Thesis Generator.
Generates Alpha, Risk, Confidence, Earlyness, Execution scores,
and structured explainability reports.
"""

from dataclasses import dataclass
import json
import logging
import time
from typing import Any, Dict, List, Optional

from app.config.settings import ScoringConfig
from app.core.database import DatabaseManager
from intelligence.market_microstructure.microstructure import MicrostructureMetrics
from intelligence.narrative.narrative_engine import NarrativeMetrics
from intelligence.token.dna import DNASnapshot
from scoring.alpha_score.alpha_calculator import AlphaCalculator
from scoring.confidence.confidence_calculator import ConfidenceCalculator
from scoring.regime.regime_engine import MarketRegime, RegimeEngine
from scoring.risk_score.risk_calculator import RiskCalculator
from security.rug_detection.rug_engine import SecurityEvaluation

logger = logging.getLogger("meme_alpha_hunter.scoring")


@dataclass
class OpportunityReport:
    mint: str
    symbol: str
    alpha_score: float
    risk_score: float
    confidence_score: float
    earlyness_score: float
    execution_score: float
    final_score: float
    regime: str
    narrative: str
    recommendation: str  # "PAPER_ENTRY", "WATCH", "WAIT_FOR_RETEST", "REJECT"
    why_ranked_high: List[str]
    why_not_higher: List[str]
    what_supports_it: List[str]
    what_could_invalidate_it: List[str]
    updated_at: float
    known_features_count: int = 13
    unknown_features_count: int = 0
    confidence_adjustment: float = 0.0
    smart_money_bridge_bonus: float = 0.0
    early_impulse_score: float = 0.0


class OpportunityScorer:
    def __init__(self, config: Optional[ScoringConfig] = None, db: Optional[DatabaseManager] = None):
        self.config = config or ScoringConfig()
        self.db = db or DatabaseManager()

    @staticmethod
    def _early_impulse_score(
        micro: MicrostructureMetrics,
        smart_money_score: float,
        earlyness: float,
        liquidity: Optional[float],
        history_count: int,
    ) -> float:
        """
        Measure acceleration/convergence before a parabolic move.

        No score is manufactured when the price history needed for acceleration
        is missing. The model rewards independent agreement among smart money,
        buyer pressure, price acceleration, volume/liquidity response and early
        lifecycle state.
        """
        if history_count < 3:
            return 0.0

        sm_component = max(0.0, min(100.0, smart_money_score))
        buyer_component = max(0.0, min(100.0, (micro.order_flow_imbalance + 1.0) * 50.0))
        ratio_component = max(0.0, min(100.0, (micro.buy_sell_ratio / 3.0) * 100.0))
        flow_component = (buyer_component * 0.60) + (ratio_component * 0.40)

        accel_component = max(0.0, min(100.0, 50.0 + (micro.price_acceleration * 500.0)))
        second_component = max(0.0, min(100.0, 50.0 + (micro.price_second_order * 350.0)))
        acceleration_component = (accel_component * 0.65) + (second_component * 0.35)

        volume_component = max(0.0, min(100.0, 50.0 + (micro.volume_acceleration * 100.0)))
        liquidity_component = max(0.0, min(100.0, 50.0 + (micro.liquidity_growth_rate * 100.0)))
        resource_component = (volume_component * 0.55) + (liquidity_component * 0.45)

        early_component = max(0.0, min(100.0, earlyness))
        execution_component = 50.0 if liquidity is not None else 25.0

        score = (
            (sm_component * 0.30) +
            (flow_component * 0.25) +
            (acceleration_component * 0.20) +
            (resource_component * 0.15) +
            (early_component * 0.08) +
            (execution_component * 0.02)
        )

        if micro.is_pre_ignition:
            score += 5.0
        if micro.money_price_divergence == "SMART_ACCUMULATION":
            score += 3.0
        if micro.money_price_divergence == "RETAIL_CHASE":
            score -= 8.0
        if micro.is_fake_breakout:
            score -= 30.0

        return round(max(0.0, min(100.0, score)), 2)

    @staticmethod
    def _smart_money_entry_bridge(
        smart_money_score: float,
        whale_netflow: float,
        earlyness: float,
        risk: float,
        early_impulse_score: float,
        is_fake_breakout: bool,
    ) -> tuple[float, str]:
        """Convert convergent early evidence into a bounded Alpha lift."""
        if is_fake_breakout or earlyness < 70.0 or risk > 45.0:
            return 0.0, ""

        sm = max(0.0, min(100.0, float(smart_money_score)))
        whale = float(whale_netflow)
        impulse = max(0.0, min(100.0, float(early_impulse_score)))

        if sm >= 85.0 and impulse >= 75.0 and whale > 0.0 and risk <= 35.0:
            return 4.0, "High-conviction early impulse with smart-money + whale-flow convergence"
        if sm >= 78.0 and impulse >= 70.0 and whale > 0.0 and risk <= 40.0:
            return 2.5, "Strong early impulse with smart-money and positive whale-flow confirmation"
        if sm >= 70.0 and impulse >= 70.0 and earlyness >= 80.0:
            return 1.0, "Early impulse confirms smart-money accumulation"

        return 0.0, ""

    def evaluate_opportunity(
        self,
        token_data: Dict[str, Any],
        security_eval: SecurityEvaluation,
        micro: MicrostructureMetrics,
        smart_money_score: float,
        whale_netflow: float,
        narrative_metrics: NarrativeMetrics,
        dna_history: List[DNASnapshot],
        age_minutes: Optional[float] = None
    ) -> OpportunityReport:
        mint = token_data.get("mint", "")
        symbol = token_data.get("symbol", "UNKNOWN")
        raw_liq = token_data.get("liquidity")
        liquidity = float(raw_liq) if raw_liq is not None else None

        alpha = AlphaCalculator.calculate(
            micro=micro,
            smart_money_score=smart_money_score,
            whale_netflow=whale_netflow,
            narrative_metrics=narrative_metrics,
            config=self.config
        )

        risk = RiskCalculator.calculate(
            security_eval=security_eval,
            micro=micro,
            liquidity_usd=liquidity
        )

        raw_confidence = ConfidenceCalculator.calculate(
            token_data=token_data,
            dna_snapshots_count=len(dna_history),
            trades_count=micro.buy_count + micro.sell_count
        )
        confidence = raw_confidence

        if age_minutes is None:
            earlyness = 50.0
            confidence = round(confidence * 0.9, 2)
        elif age_minutes < 60.0:
            earlyness = max(100.0 - (age_minutes / 60.0) * 30.0, 70.0)
        elif age_minutes < 1440.0:
            earlyness = max(70.0 - (age_minutes / 1440.0) * 30.0, 40.0)
        else:
            earlyness = 30.0

        if liquidity is None:
            execution_score = 35.0
            confidence = round(confidence * 0.8, 2)
        elif liquidity > 1_000_000.0:
            execution_score = 95.0
        elif liquidity > 100_000.0:
            execution_score = 85.0
        elif liquidity > 25_000.0:
            execution_score = 75.0
        elif liquidity > 5_000.0:
            execution_score = 60.0
        else:
            execution_score = 35.0

        features_known = {
            "liquidity": liquidity is not None,
            "age_minutes": age_minutes is not None,
            "narrative_heat": narrative_metrics.heat_score is not None,
            "holders_count": token_data.get("holders_count") is not None,
            "volume_24h": token_data.get("volume_24h") is not None,
            "lp_locked_pct": security_eval.lp_locked_pct is not None,
            "top10_holder_pct": security_eval.top10_holder_pct is not None,
            "dev_holding_pct": security_eval.dev_holding_pct is not None,
            "smart_money": True,
            "whale_netflow": True,
            "microstructure": True,
            "mint_auth_revoked": True,
            "freeze_auth_revoked": True,
        }
        known_count = sum(1 for v in features_known.values() if v)
        unknown_count = sum(1 for v in features_known.values() if not v)
        confidence_adj = round(confidence - raw_confidence, 2)

        regime = RegimeEngine.classify(
            token_data=token_data,
            micro_metrics=micro,
            smart_money_score=smart_money_score,
            whale_netflow=whale_netflow
        )

        early_impulse = self._early_impulse_score(
            micro=micro,
            smart_money_score=smart_money_score,
            earlyness=earlyness,
            liquidity=liquidity,
            history_count=len(dna_history),
        )

        bridge_bonus, bridge_reason = self._smart_money_entry_bridge(
            smart_money_score=smart_money_score,
            whale_netflow=whale_netflow,
            earlyness=earlyness,
            risk=risk,
            early_impulse_score=early_impulse,
            is_fake_breakout=micro.is_fake_breakout,
        )

        alpha = round(min(alpha + bridge_bonus, 100.0), 2)
        final_score = (
            (alpha * 0.45) +
            ((100.0 - risk) * 0.25) +
            (confidence * 0.15) +
            (earlyness * 0.15)
        )

        if security_eval.status == "HARD_REJECT":
            final_score = min(final_score, 20.0)
            recommendation = "REJECT"
        elif micro.is_fake_breakout:
            recommendation = "REJECT"
        elif alpha >= self.config.min_alpha_score and risk <= self.config.max_risk_score and final_score >= self.config.min_opportunity_score:
            recommendation = "PAPER_ENTRY"
        elif alpha >= 55.0 and risk <= 55.0:
            recommendation = "WAIT_FOR_RETEST" if micro.price_velocity > 0.20 else "WATCH"
        else:
            recommendation = "REJECT"

        why_high: List[str] = []
        why_not_higher: List[str] = []
        supports: List[str] = []
        invalidates: List[str] = []

        if alpha > 75.0:
            why_high.append(f"High multi-factor Alpha ({alpha:.1f}) with positive microstructure")
        if smart_money_score > 75.0:
            why_high.append(f"Strong Smart Money backing (Score: {smart_money_score:.1f})")
        if early_impulse >= 70.0:
            why_high.append(f"Early Impulse Score {early_impulse:.1f}: acceleration + buyer pressure + resource response are aligned")
        if bridge_reason:
            why_high.append(f"Entry bridge: {bridge_reason} (+{bridge_bonus:.2f} Alpha)")
        if micro.is_pre_ignition:
            why_high.append("Pre-ignition signature: expanding liquidity + accelerating buyers before parabolic spike")

        if risk > 30.0:
            why_not_higher.append(f"Elevated risk factors (Risk Score: {risk:.1f})")
        if liquidity is None:
            why_not_higher.append("Liquidity pool depth is unverified")
        elif liquidity < 50_000.0:
            why_not_higher.append(f"Moderate liquidity pool (${liquidity:,.0f})")

        if age_minutes is None:
            why_not_higher.append("Token age is unknown (unverified pool creation timestamp)")
        elif earlyness < 50.0:
            why_not_higher.append("Token is established / older lifecycle stage")

        if smart_money_score >= 70.0 and whale_netflow <= 0.0:
            why_not_higher.append("Smart Money lacks positive whale-flow confirmation")
        if smart_money_score >= 78.0 and earlyness < 70.0:
            why_not_higher.append("Strong Smart Money is not early enough for entry acceleration")
        if 0.0 < early_impulse < 60.0:
            why_not_higher.append(f"Early impulse is not yet strong enough ({early_impulse:.1f})")

        supports.append(f"Market Regime: {regime.value}")
        supports.append(f"Narrative: {narrative_metrics.name} ({narrative_metrics.stage})")
        supports.append(f"Whale Netflow: ${whale_netflow:+,.0f}")
        supports.append(f"Early Impulse: {early_impulse:.1f}")

        invalidates.append("Sudden smart money net distribution")
        invalidates.append("Liquidity pool withdrawal or drain")
        invalidates.append("Security authority tampering or freeze action")
        invalidates.append("Loss of buyer acceleration / renewed retail chase")

        report = OpportunityReport(
            mint=mint,
            symbol=symbol,
            alpha_score=round(alpha, 2),
            risk_score=round(risk, 2),
            confidence_score=round(confidence, 2),
            earlyness_score=round(earlyness, 2),
            execution_score=round(execution_score, 2),
            final_score=round(final_score, 2),
            regime=regime.value,
            narrative=narrative_metrics.name,
            recommendation=recommendation,
            why_ranked_high=why_high,
            why_not_higher=why_not_higher,
            what_supports_it=supports,
            what_could_invalidate_it=invalidates,
            updated_at=time.time(),
            known_features_count=known_count,
            unknown_features_count=unknown_count,
            confidence_adjustment=confidence_adj,
            smart_money_bridge_bonus=round(bridge_bonus, 2),
            early_impulse_score=early_impulse,
        )

        try:
            self.db.upsert_opportunity_score({
                "mint": report.mint,
                "symbol": report.symbol,
                "alpha_score": report.alpha_score,
                "risk_score": report.risk_score,
                "confidence_score": report.confidence_score,
                "earlyness_score": report.earlyness_score,
                "execution_score": report.execution_score,
                "final_score": report.final_score,
                "regime": report.regime,
                "narrative": report.narrative,
                "recommendation": report.recommendation,
                "explanation_json": json.dumps({
                    "why_ranked_high": report.why_ranked_high,
                    "why_not_higher": report.why_not_higher,
                    "what_supports_it": report.what_supports_it,
                    "what_could_invalidate_it": report.what_could_invalidate_it,
                    "smart_money_bridge_bonus": report.smart_money_bridge_bonus,
                    "early_impulse_score": report.early_impulse_score,
                }),
                "updated_at": report.updated_at
            })
        except Exception as e:
            logger.error(f"Failed to persist opportunity score for {mint}: {e}")

        return report
