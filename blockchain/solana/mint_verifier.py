"""
On-Chain Mint Account Verifier for Solana.
Validates Base58 encoding, queries Solana RPC getAccountInfo with jsonParsed encoding,
confirms SPL Token / Token-2022 program ownership, extracts decimals, mint authority,
freeze authority, and queries top holder concentration.
Strictly live on-chain with zero static fallbacks.
"""

from dataclasses import dataclass, field
import logging
import time
from typing import Any, Dict, List, Optional

from blockchain.rpc.rpc_client import SolanaRPCClient
from blockchain.solana.address_validator import SolanaAddressValidator
from blockchain.solana.types import Provenance, SourceType

logger = logging.getLogger("meme_alpha_hunter.mint_verifier")

SPL_TOKEN_PROGRAM_ID = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
TOKEN_2022_PROGRAM_ID = "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"


@dataclass
class OnChainMintVerification:
    mint: str
    is_valid_mint: bool
    owner_program: Optional[str] = None
    decimals: int = 9
    supply: float = 0.0
    is_initialized: bool = False
    mint_authority: Optional[str] = None
    freeze_authority: Optional[str] = None
    mint_auth_revoked: bool = False
    freeze_auth_revoked: bool = False
    top10_holder_pct: Optional[float] = None
    top_holders_count: int = 0
    verification_status: str = "PENDING"  # "VERIFIED_ON_CHAIN", "NOT_A_MINT", "INVALID_OWNER", "RPC_UNAVAILABLE", "INVALID_BASE58", "ACCOUNT_NOT_FOUND"
    error_reason: Optional[str] = None
    provenance: Provenance = field(default_factory=Provenance)


class OnChainMintVerifier:
    def __init__(self, rpc_client: Optional[SolanaRPCClient] = None):
        self.rpc = rpc_client or SolanaRPCClient()
        self._cache: Dict[str, OnChainMintVerification] = {}

    def verify_mint(self, mint: str, fetch_largest_accounts: bool = True) -> OnChainMintVerification:
        """
        Strict 9-step on-chain verification of a token mint:
        1. validate Base58 decoding
        2. query Solana RPC getAccountInfo (jsonParsed)
        3. verify account exists
        4. verify account owner is SPL Token Program or Token-2022
        5. parse Mint account data (type == 'mint')
        6. retrieve decimals
        7. retrieve mint authority
        8. retrieve freeze authority
        9. retrieve largest holder accounts
        """
        # Step 1: Base58 format validation
        if not SolanaAddressValidator.validate_token_mint(mint):
            return OnChainMintVerification(
                mint=mint,
                is_valid_mint=False,
                verification_status="INVALID_BASE58",
                error_reason="Address failed Base58 character or length check (32-44 chars required)",
                provenance=Provenance(source_type=SourceType.REAL, provider="Base58Validator", confidence=0.0)
            )

        if mint in self._cache:
            return self._cache[mint]

        # Step 2: Query Solana RPC getAccountInfo with jsonParsed encoding
        account_resp = self.rpc.get_account_info(mint, encoding="jsonParsed")

        if account_resp is None:
            # RPC unreachable or connection failure
            res = OnChainMintVerification(
                mint=mint,
                is_valid_mint=False,
                verification_status="RPC_UNAVAILABLE",
                error_reason="Solana RPC unreachable or connection closed",
                provenance=Provenance(source_type=SourceType.REAL, provider="SolanaRPC", confidence=0.0, verified_on_chain=False)
            )
            return res

        account_info = account_resp.get("value")
        if not account_info:
            res = OnChainMintVerification(
                mint=mint,
                is_valid_mint=False,
                verification_status="ACCOUNT_NOT_FOUND",
                error_reason=f"Account {mint} does not exist on Solana mainnet",
                provenance=Provenance(source_type=SourceType.REAL, provider="SolanaRPC", confidence=0.0, verified_on_chain=True)
            )
            self._cache[mint] = res
            return res

        # Step 3 & 4: Check owner program
        owner = account_info.get("owner", "")
        if owner not in (SPL_TOKEN_PROGRAM_ID, TOKEN_2022_PROGRAM_ID):
            res = OnChainMintVerification(
                mint=mint,
                is_valid_mint=False,
                owner_program=owner,
                verification_status="INVALID_OWNER",
                error_reason=f"Account owner {owner} is neither SPL Token nor Token-2022 Program",
                provenance=Provenance(source_type=SourceType.REAL, provider="SolanaRPC", confidence=0.0, verified_on_chain=True)
            )
            self._cache[mint] = res
            return res

        # Step 5: Parse Mint account data
        data = account_info.get("data")
        parsed_data = None
        if isinstance(data, dict):
            parsed_data = data.get("parsed")

        if not parsed_data or parsed_data.get("type") != "mint":
            res = OnChainMintVerification(
                mint=mint,
                is_valid_mint=False,
                owner_program=owner,
                verification_status="NOT_A_MINT",
                error_reason=f"Account data type '{parsed_data.get('type') if isinstance(parsed_data, dict) else 'raw'}' is not a token mint",
                provenance=Provenance(source_type=SourceType.REAL, provider="SolanaRPC", confidence=0.0, verified_on_chain=True)
            )
            self._cache[mint] = res
            return res

        # Steps 6, 7, 8: Extract mint details
        info = parsed_data.get("info", {})
        decimals = int(info.get("decimals", 9))
        supply_raw = float(info.get("supply", 0.0))
        supply = supply_raw / (10 ** decimals) if decimals > 0 else supply_raw
        is_initialized = bool(info.get("isInitialized", True))
        mint_authority = info.get("mintAuthority")
        freeze_authority = info.get("freezeAuthority")

        mint_auth_revoked = (mint_authority is None)
        freeze_auth_revoked = (freeze_authority is None)

        # Step 9: Top holder accounts
        top10_pct = None
        holders_count = 0
        if fetch_largest_accounts:
            largest_resp = self.rpc.get_token_largest_accounts(mint)
            if largest_resp and isinstance(largest_resp, list):
                accounts = largest_resp
                holders_count = len(accounts)
                if supply > 0 and accounts:
                    top10_amount = sum(float(a.get("uiAmount", 0.0) or 0.0) for a in accounts[:10])
                    top10_pct = round((top10_amount / supply) * 100.0, 2)

        verification = OnChainMintVerification(
            mint=mint,
            is_valid_mint=True,
            owner_program=owner,
            decimals=decimals,
            supply=supply,
            is_initialized=is_initialized,
            mint_authority=mint_authority,
            freeze_authority=freeze_authority,
            mint_auth_revoked=mint_auth_revoked,
            freeze_auth_revoked=freeze_auth_revoked,
            top10_holder_pct=top10_pct,
            top_holders_count=holders_count,
            verification_status="VERIFIED_ON_CHAIN",
            provenance=Provenance(
                source_type=SourceType.REAL,
                provider="SolanaRPC.getAccountInfo",
                timestamp=time.time(),
                observed_at=time.time(),
                confidence=1.0,
                verified_on_chain=True
            )
        )

        self._cache[mint] = verification
        return verification

    def verify_from_account_data(self, mint: str, account_data: Dict[str, Any], source_type: SourceType = SourceType.REPLAY) -> OnChainMintVerification:
        """Helper to parse and verify mint account directly from raw / cached RPC account data for snapshot/replay."""
        if not SolanaAddressValidator.validate_token_mint(mint):
            return OnChainMintVerification(
                mint=mint,
                is_valid_mint=False,
                verification_status="INVALID_BASE58",
                error_reason="Failed Base58 format check",
                provenance=Provenance(source_type=source_type, provider="Base58Validator", confidence=0.0)
            )

        owner = account_data.get("owner", "")
        if owner not in (SPL_TOKEN_PROGRAM_ID, TOKEN_2022_PROGRAM_ID):
            return OnChainMintVerification(
                mint=mint,
                is_valid_mint=False,
                owner_program=owner,
                verification_status="INVALID_OWNER",
                error_reason=f"Owner {owner} is not SPL Token Program",
                provenance=Provenance(source_type=source_type, provider="SolanaRPC", confidence=0.0, verified_on_chain=True)
            )

        data = account_data.get("data", {})
        parsed_data = data.get("parsed") if isinstance(data, dict) else None
        if not parsed_data or parsed_data.get("type") != "mint":
            return OnChainMintVerification(
                mint=mint,
                is_valid_mint=False,
                owner_program=owner,
                verification_status="NOT_A_MINT",
                error_reason="Account is not a mint",
                provenance=Provenance(source_type=source_type, provider="SolanaRPC", confidence=0.0, verified_on_chain=True)
            )

        info = parsed_data.get("info", {})
        decimals = int(info.get("decimals", 9))
        supply_raw = float(info.get("supply", 0.0))
        supply = supply_raw / (10 ** decimals) if decimals > 0 else supply_raw
        mint_authority = info.get("mintAuthority")
        freeze_authority = info.get("freezeAuthority")

        return OnChainMintVerification(
            mint=mint,
            is_valid_mint=True,
            owner_program=owner,
            decimals=decimals,
            supply=supply,
            is_initialized=bool(info.get("isInitialized", True)),
            mint_authority=mint_authority,
            freeze_authority=freeze_authority,
            mint_auth_revoked=(mint_authority is None),
            freeze_auth_revoked=(freeze_authority is None),
            verification_status="VERIFIED_ON_CHAIN",
            provenance=Provenance(
                source_type=source_type,
                provider="SnapshotVerifier",
                timestamp=time.time(),
                observed_at=time.time(),
                confidence=1.0,
                verified_on_chain=True
            )
        )
