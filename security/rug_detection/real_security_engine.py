"""
Real On-Chain Security and Rug Pull Detection Engine for Solana.
Uses verified on-chain mint account data, holder distribution, and LP lock status.
Explicitly marks unverified attributes as UNKNOWN and penalizes confidence.
Zero manufactured safe scores.
"""

from dataclasses import dataclass, field
import json
import logging
import time
from typing import Any, Dict, List, Optional

from app.config.settings import SecurityConfig
from app.core.database import DatabaseManager
from blockchain.solana.mint_verifier import OnChainMintVerification, OnChainMintVerifier
from blockchain.solana.types import Provenance, SourceType

logger = logging.getLogger("meme_alpha_hunter.real_security")


@dataclass
class RealSecurityEvaluation:
    mint: str
    security_score: float  # 0 to 100
    rug_probability: float  # 0 to 100
    confidence: float       # 0.0 to 1.0 (penalized if attributes UNKNOWN)
    status: str             # "SAFE", "WARNING", "HARD_REJECT", "UNVERIFIED"
    mint_auth_status: str   # "REVOKED_SAFE", "ACTIVE_DANGEROUS", "UNKNOWN"
    freeze_auth_status: str # "REVOKED_SAFE", "ACTIVE_DANGEROUS", "UNKNOWN"
    holder_concentration_status: str # "SAFE_DISTRIBUTED", "DANGEROUS_CONCENTRATED", "UNKNOWN"
    lp_lock_status: str     # "LOCKED", "BURNED", "UNLOCKED_DANGEROUS", "UNKNOWN"
    top10_holder_pct: Optional[float] = None
    dev_holding_pct: Optional[float] = None
    rejection_reasons: List[str] = field(default_factory=list)
    unknown_attributes: List[str] = field(default_factory=list)
    evaluated_at: float = field(default_factory=time.time)
    provenance: Provenance = field(default_factory=Provenance)


class RealSecurityEngine:
    def __init__(self, config: Optional[SecurityConfig] = None, mint_verifier: Optional[OnChainMintVerifier] = None, db: Optional[DatabaseManager] = None):
        self.config = config or SecurityConfig()
        self.verifier = mint_verifier or OnChainMintVerifier()
        self.db = db or DatabaseManager()

    def evaluate_token(
        self,
        mint: str,
        verification: Optional[OnChainMintVerification] = None,
        lp_locked_pct: Optional[float] = None,
        dev_holding_pct: Optional[float] = None,
        cluster_risk_multiplier: float = 1.0
    ) -> RealSecurityEvaluation:
        """
        Evaluates token security using strict on-chain data.
        """
        if not verification:
            verification = self.verifier.verify_mint(mint)

        reasons: List[str] = []
        unknowns: List[str] = []
        is_hard_reject = False
        penalty = 0.0
        confidence = 1.0

        # 1. Base58 & Mint account existence
        if not verification.is_valid_mint:
            reasons.append(f"INVALID ON-CHAIN MINT: {verification.error_reason or 'Failed on-chain validation'}")
            return RealSecurityEvaluation(
                mint=mint,
                security_score=0.0,
                rug_probability=100.0,
                confidence=1.0,
                status="HARD_REJECT",
                mint_auth_status="UNKNOWN",
                freeze_auth_status="UNKNOWN",
                holder_concentration_status="UNKNOWN",
                lp_lock_status="UNKNOWN",
                rejection_reasons=reasons,
                unknown_attributes=["onchain_account"],
                provenance=verification.provenance
            )

        # 2. Mint Authority
        if verification.mint_authority is None:
            mint_status = "REVOKED_SAFE"
        else:
            mint_status = "ACTIVE_DANGEROUS"
            penalty += 35.0
            reasons.append(f"Mint Authority is ACTIVE ({verification.mint_authority[:6]}...): Deployer can mint infinite tokens")
            if self.config.hard_reject_freeze_enabled:
                is_hard_reject = True

        # 3. Freeze Authority
        if verification.freeze_authority is None:
            freeze_status = "REVOKED_SAFE"
        else:
            freeze_status = "ACTIVE_DANGEROUS"
            penalty += 45.0
            reasons.append(f"Freeze Authority is ACTIVE ({verification.freeze_authority[:6]}...): Creator can freeze transfers (Honeypot)")
            if self.config.hard_reject_freeze_enabled:
                is_hard_reject = True

        # 4. Holder Concentration (from on-chain top holders)
        top10_pct = verification.top10_holder_pct
        if top10_pct is not None:
            if top10_pct > self.config.max_top10_holders_percent:
                holder_status = "DANGEROUS_CONCENTRATED"
                penalty += min((top10_pct - self.config.max_top10_holders_percent) * 1.5, 40.0)
                reasons.append(f"Top 10 holders control {top10_pct:.1f}% (> {self.config.max_top10_holders_percent}% max limit)")
                if top10_pct >= 85.0:
                    is_hard_reject = True
            else:
                holder_status = "SAFE_DISTRIBUTED"
        else:
            holder_status = "UNKNOWN"
            unknowns.append("top10_holder_distribution")
            confidence -= 0.25
            penalty += 15.0  # Conservative unknown penalty

        # 5. Dev / Creator holding
        if dev_holding_pct is not None:
            if dev_holding_pct > self.config.max_creator_allocation_percent:
                penalty += (dev_holding_pct - self.config.max_creator_allocation_percent) * 1.5
                reasons.append(f"Creator holds {dev_holding_pct:.1f}% (> {self.config.max_creator_allocation_percent}% limit)")
                if dev_holding_pct >= 40.0:
                    is_hard_reject = True
        else:
            unknowns.append("creator_dev_holding")
            confidence -= 0.15

        # 6. LP Lock / Burn
        if lp_locked_pct is not None:
            if lp_locked_pct >= 90.0:
                lp_status = "LOCKED"
            elif lp_locked_pct >= self.config.min_lp_locked_percent:
                lp_status = "BURNED"
            else:
                lp_status = "UNLOCKED_DANGEROUS"
                penalty += 30.0
                reasons.append(f"LP Lock is {lp_locked_pct:.1f}% (< {self.config.min_lp_locked_percent}% required)")
                if lp_locked_pct < 10.0:
                    is_hard_reject = True
        else:
            lp_status = "UNKNOWN"
            unknowns.append("lp_lock_burn_status")
            confidence -= 0.20
            penalty += 15.0

        # Apply Cluster Risk multiplier if Sybil cluster detected
        if cluster_risk_multiplier > 1.0:
            penalty *= cluster_risk_multiplier
            reasons.append(f"Sybil cluster multiplier ({cluster_risk_multiplier:.1f}x) applied to risk score")

        # Composite score
        rug_prob = round(min(max(penalty, 0.0), 100.0), 2)
        security_score = round(max(0.0, 100.0 - rug_prob), 2)
        confidence = round(max(confidence, 0.1), 2)

        if is_hard_reject or rug_prob > self.config.max_rug_probability_for_sniper:
            status = "HARD_REJECT"
        elif confidence < 0.60:
            status = "UNVERIFIED"
        elif rug_prob > 30.0:
            status = "WARNING"
        else:
            status = "SAFE"

        eval_result = RealSecurityEvaluation(
            mint=mint,
            security_score=security_score,
            rug_probability=rug_prob,
            confidence=confidence,
            status=status,
            mint_auth_status=mint_status,
            freeze_auth_status=freeze_status,
            holder_concentration_status=holder_status,
            lp_lock_status=lp_status,
            top10_holder_pct=top10_pct,
            dev_holding_pct=dev_holding_pct,
            rejection_reasons=reasons,
            unknown_attributes=unknowns,
            evaluated_at=time.time(),
            provenance=verification.provenance
        )

        # Persist to database
        try:
            self.db.upsert_security_report({
                "mint": eval_result.mint,
                "security_score": eval_result.security_score,
                "rug_probability": eval_result.rug_probability,
                "mint_auth_revoked": 1 if mint_status == "REVOKED_SAFE" else 0,
                "freeze_auth_revoked": 1 if freeze_status == "REVOKED_SAFE" else 0,
                "lp_locked_pct": lp_locked_pct or 0.0,
                "top10_holder_pct": top10_pct or 0.0,
                "dev_holding_pct": dev_holding_pct or 0.0,
                "rejection_reasons": json.dumps(eval_result.rejection_reasons),
                "status": eval_result.status,
                "evaluated_at": eval_result.evaluated_at
            })
        except Exception as e:
            logger.error(f"Failed to persist real security report: {e}")

        return eval_result
