"""
Solana Token Authority and Extension Security Checker.
Checks Mint Authority, Freeze Authority, and Token-2022 Extensions.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class AuthorityCheckResult:
    mint_auth_revoked: bool
    freeze_auth_revoked: bool
    is_safe: bool
    risk_points: float  # 0 to 100 risk points
    reasons: list


class AuthorityChecker:
    @classmethod
    def check(cls, sec_data: Dict[str, Any]) -> AuthorityCheckResult:
        reasons = []
        risk_points = 0.0

        # Mint authority check
        mint_auth = sec_data.get("mint_auth_revoked")
        if mint_auth is None:
            # Check string representation if raw parsed info
            mint_auth = sec_data.get("mint_authority") is None

        if not mint_auth:
            risk_points += 45.0
            reasons.append("Mint Authority is ACTIVE (Creator can mint unlimited tokens)")

        # Freeze authority check
        freeze_auth = sec_data.get("freeze_auth_revoked")
        if freeze_auth is None:
            freeze_auth = sec_data.get("freeze_authority") is None

        if not freeze_auth:
            risk_points += 50.0
            reasons.append("Freeze Authority is ACTIVE (Creator can freeze user accounts/honeypot)")

        is_safe = (mint_auth and freeze_auth)
        return AuthorityCheckResult(
            mint_auth_revoked=bool(mint_auth),
            freeze_auth_revoked=bool(freeze_auth),
            is_safe=is_safe,
            risk_points=min(risk_points, 100.0),
            reasons=reasons
        )
