"""
Composite Opportunity Scorer & Thesis Generator.
Generates Alpha, Risk, Confidence, Earlyness, Execution scores,
and structured explainability reports.
"""

from dataclasses import dataclass, asdict
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


class OpportunityScorer:
    def __init__(self, config: Optional[ScoringConfig] = None, db: Optional[DatabaseManager] = None):
        self.config = config or ScoringConfig()
        self.db = db or DatabaseManager()

    def evaluate_opportunity(
        self,
        token_data: Dict[str, Any],
        security_eval: SecurityEvaluation,
        micro: MicrostructureMetrics,
        smart_money_score: float,
        whale_netflow: float,
        narrative_metrics: NarrativeMetrics,
        dna_history: List[DNASnapshot],
        age_minutes: float = 30.0
    ) -> OpportunityReport:
        mint = token_data.get("mint", "")
        symbol = token_data.get("symbol", "UNKNOWN")
        raw_liq = token_data.get("liquidity")
        liquidity = float(raw_liq) if raw_liq is not None else 0.0

        # 1. Calculate Core Scores
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

        confidence = ConfidenceCalculator.calculate(
            token_data=token_data,
            dna_snapshots_count=len(dna_history),
            trades_count=micro.buy_count + micro.sell_count
        )

        # 2. Earlyness Score (Higher if fresh/young token or early accumulation phase)
        if age_minutes < 60.0:
            earlyness = max(100.0 - (age_minutes / 60.0) * 30.0, 70.0)
        elif age_minutes < 1440.0:  # < 24h
            earlyness = max(70.0 - (age_minutes / 1440.0) * 30.0, 40.0)
        else:
            earlyness = 30.0

        # 3. Execution Score (Liquidity depth and slippage friendliness)
        if liquidity > 1_000_000.0:
            execution_score = 95.0
        elif liquidity > 100_000.0:
            execution_score = 85.0
        elif liquidity > 25_000.0:
            execution_score = 75.0
        elif liquidity > 5_000.0:
            execution_score = 60.0
        else:
            execution_score = 35.0

        # 4. Regime classification
        regime = RegimeEngine.classify(
            token_data=token_data,
            micro_metrics=micro,
            smart_money_score=smart_money_score,
            whale_netflow=whale_netflow
        )

        # 5. Composite Final Score
        # Opportunity = (Alpha * 0.45) + ((100 - Risk) * 0.25) + (Confidence * 0.15) + (Earlyness * 0.15)
        final_score = (
            (alpha * 0.45) +
            ((100.0 - risk) * 0.25) +
            (confidence * 0.15) +
            (earlyness * 0.15)
        )

        # Hard reject override if security is critical
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

        # 6. Structured Explainability
        why_high = []
        why_not_higher = []
        supports = []
        invalidates = []

        if alpha > 75.0:
            why_high.append(f"High multi-factor Alpha ({alpha:.1f}) with positive microstructure")
        if smart_money_score > 75.0:
            why_high.append(f"Strong Smart Money backing (Score: {smart_money_score:.1f})")
        if micro.is_pre_ignition:
            why_high.append("Pre-ignition signature: expanding liquidity + accelerating buyers before parabolic spike")

        if risk > 30.0:
            why_not_higher.append(f"Elevated risk factors (Risk Score: {risk:.1f})")
        if liquidity < 50_000.0:
            why_not_higher.append(f"Moderate liquidity pool (${liquidity:,.0f})")
        if earlyness < 50.0:
            why_not_higher.append("Token is established / older lifecycle stage")

        supports.append(f"Market Regime: {regime.value}")
        supports.append(f"Narrative: {narrative_metrics.name} ({narrative_metrics.stage})")
        supports.append(f"Whale Netflow: ${whale_netflow:+,.0f}")

        invalidates.append("Sudden smart money net distribution")
        invalidates.append("Liquidity pool withdrawal or drain")
        invalidates.append("Security authority tampering or freeze action")

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
            updated_at=time.time()
        )

        # Persist to database
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
                    "what_could_invalidate_it": report.what_could_invalidate_it
                }),
                "updated_at": report.updated_at
            })
        except Exception as e:
            logger.error(f"Failed to persist opportunity score for {mint}: {e}")

        return report
