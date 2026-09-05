"""
Composite Security and Rug Pull Detection Engine for Solana tokens.
Calculates Security Score (0-100), Rug Probability (0-100), and issues HARD REJECTs.
"""

from dataclasses import dataclass, asdict
import json
import logging
import time
from typing import Any, Dict, List, Optional

from app.config.settings import SecurityConfig
from app.core.database import DatabaseManager
from security.liquidity_risk.liquidity_checker import LiquidityRiskChecker
from security.token_security.authority_checker import AuthorityChecker
from security.wallet_risk.concentration_checker import ConcentrationChecker

logger = logging.getLogger("meme_alpha_hunter.security")


@dataclass
class SecurityEvaluation:
    mint: str
    security_score: float  # 0 to 100 (higher = safer)
    rug_probability: float  # 0 to 100 (higher = riskier)
    mint_auth_revoked: bool
    freeze_auth_revoked: bool
    lp_locked_pct: float
    top10_holder_pct: float
    dev_holding_pct: float
    is_honeypot: bool
    is_wash_traded: bool
    status: str  # "SAFE", "WARNING", "HARD_REJECT"
    rejection_reasons: List[str]
    evaluated_at: float


class RugDetectionEngine:
    def __init__(self, config: Optional[SecurityConfig] = None, db: Optional[DatabaseManager] = None):
        self.config = config or SecurityConfig()
        self.db = db or DatabaseManager()

    def evaluate(self, mint: str, sec_data: Dict[str, Any]) -> SecurityEvaluation:
        reasons: List[str] = []
        is_hard_reject = False

        # 1. Authority checks
        auth_res = AuthorityChecker.check(sec_data)
        if not auth_res.mint_auth_revoked and self.config.require_mint_authority_revoked:
            reasons.extend(auth_res.reasons)
            if self.config.hard_reject_freeze_enabled:
                is_hard_reject = True
        if not auth_res.freeze_auth_revoked and self.config.require_freeze_authority_revoked:
            reasons.extend(auth_res.reasons)
            if self.config.hard_reject_freeze_enabled:
                is_hard_reject = True

        # 2. Liquidity risk checks
        liq_res = LiquidityRiskChecker.check(sec_data, min_lp_locked_pct=self.config.min_lp_locked_percent)
        if not liq_res.is_locked_adequate:
            reasons.extend(liq_res.reasons)
            if liq_res.lp_locked_pct < 10.0:
                is_hard_reject = True

        # 3. Holder concentration checks
        conc_res = ConcentrationChecker.check(
            sec_data,
            max_top10_pct=self.config.max_top10_holders_percent,
            max_dev_pct=self.config.max_creator_allocation_percent
        )
        if not conc_res.is_acceptable:
            reasons.extend(conc_res.reasons)
            if conc_res.dev_holding_pct > 50.0 and self.config.hard_reject_extreme_concentration:
                is_hard_reject = True

        # 4. Honeypot & Wash Trading checks
        is_honeypot = bool(sec_data.get("is_honeypot", False))
        is_wash_traded = bool(sec_data.get("is_wash_traded", False))

        if is_honeypot:
            reasons.append("HONEYPOT DETECTED: Sell transactions fail on-chain")
            is_hard_reject = True

        if is_wash_traded:
            reasons.append("WASH TRADING DETECTED: High artificial volume from single entity cluster")

        # Composite Risk Calculation (0 - 100)
        total_penalty = (
            auth_res.risk_points * 0.35 +
            liq_res.risk_points * 0.25 +
            conc_res.risk_points * 0.25 +
            (40.0 if is_wash_traded else 0.0) +
            (100.0 if is_honeypot else 0.0)
        )

        rug_prob = min(max(total_penalty, 0.0), 100.0)
        security_score = max(0.0, 100.0 - rug_prob)

        # Final classification
        if is_hard_reject or rug_prob > self.config.max_rug_probability_for_sniper or security_score < self.config.min_security_score_for_entry:
            status = "HARD_REJECT"
        elif rug_prob > 25.0:
            status = "WARNING"
        else:
            status = "SAFE"

        eval_result = SecurityEvaluation(
            mint=mint,
            security_score=round(security_score, 2),
            rug_probability=round(rug_prob, 2),
            mint_auth_revoked=auth_res.mint_auth_revoked,
            freeze_auth_revoked=auth_res.freeze_auth_revoked,
            lp_locked_pct=liq_res.lp_locked_pct,
            top10_holder_pct=conc_res.top10_holder_pct,
            dev_holding_pct=conc_res.dev_holding_pct,
            is_honeypot=is_honeypot,
            is_wash_traded=is_wash_traded,
            status=status,
            rejection_reasons=list(set(reasons)),
            evaluated_at=time.time()
        )

        # Persist to database
        try:
            self.db.upsert_security_report({
                "mint": eval_result.mint,
                "security_score": eval_result.security_score,
                "rug_probability": eval_result.rug_probability,
                "mint_auth_revoked": 1 if eval_result.mint_auth_revoked else 0,
                "freeze_auth_revoked": 1 if eval_result.freeze_auth_revoked else 0,
                "lp_locked_pct": eval_result.lp_locked_pct,
                "top10_holder_pct": eval_result.top10_holder_pct,
                "dev_holding_pct": eval_result.dev_holding_pct,
                "rejection_reasons": json.dumps(eval_result.rejection_reasons),
                "status": eval_result.status,
                "evaluated_at": eval_result.evaluated_at
            })
        except Exception as e:
            logger.error(f"Failed to persist security report for {mint}: {e}")

        return eval_result
