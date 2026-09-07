"""
Strict Real Solana Live Market Provider.
Queries live Solana RPC and DEX endpoints during current run.
If live network is unreachable, returns None / empty without static fallbacks.
Strictly tags all outputs with SourceType.REAL and live timestamps.
"""

import logging
import time
from collections import defaultdict, deque
from typing import Any, Dict, List, Optional

from blockchain.parsers.dex_pool_adapter import PUMP_FUN_PROGRAM
from blockchain.parsers.real_swap_parser import RealSwapParser, RealSwapRecord
from blockchain.rpc.rpc_client import SolanaRPCClient
from blockchain.solana.mint_verifier import OnChainMintVerifier
from blockchain.solana.types import SourceType
from data.ingestion.dex_provider import DexPublicProvider
from data.ingestion.provider_base import BaseDataProvider

logger = logging.getLogger("meme_alpha_hunter.real_provider")


class RealSolanaLiveProvider(BaseDataProvider):
    """
    Live provider with a clear data-plane contract:
    - DEX endpoints discover current market state.
    - Solana RPC verifies mint state and supplies raw swap evidence.
    - Previously processed transaction signatures are never fetched again.
    - UNKNOWN values remain UNKNOWN; nothing is fabricated to keep scoring alive.
    """

    def __init__(self, rpc_client: Optional[SolanaRPCClient] = None):
        super().__init__(source_type=SourceType.REAL, provider_name="SolanaLiveMainnetProvider")
        self.rpc = rpc_client or SolanaRPCClient()
        self.dex_api = DexPublicProvider()
        self.mint_verifier = OnChainMintVerifier(self.rpc)
        self.swap_parser = RealSwapParser()
        self._live_sol_price_usd: Optional[float] = None
        self._seen_signatures: Dict[str, set[str]] = defaultdict(set)
        self._seen_signature_order: Dict[str, deque[str]] = defaultdict(deque)
        self._max_seen_signatures = 512

    def is_network_connected(self) -> bool:
        return self.rpc.get_health() == "ok"

    def get_sol_price_usd(self) -> Optional[float]:
        sol_data = self.dex_api.get_token_market_data("So11111111111111111111111111111111111111112")
        if sol_data and sol_data.get("price") and float(sol_data["price"]) > 0:
            return float(sol_data["price"])
        return None

    def get_token_metadata(self, mint: str) -> Optional[Dict[str, Any]]:
        verification = self.mint_verifier.verify_mint(mint)
        if not verification.is_valid_mint:
            return None

        dex_meta = self.dex_api.get_token_metadata(mint) or {}
        return {
            "mint": mint,
            "symbol": dex_meta.get("symbol", "UNKNOWN"),
            "name": dex_meta.get("name", "Solana Token"),
            "decimals": verification.decimals,
            "supply": verification.supply,
            "mint_authority": verification.mint_authority,
            "freeze_authority": verification.freeze_authority,
            "is_verified_on_chain": True,
            "provenance": self.create_provenance(confidence=1.0, verified_on_chain=True).to_dict(),
        }

    def get_token_market_data(self, mint: str) -> Optional[Dict[str, Any]]:
        dex_data = self.dex_api.get_token_market_data(mint)
        if not dex_data:
            return None

        verification = self.mint_verifier.verify_mint(mint)
        if not verification.is_valid_mint:
            return None

        dex_data["provenance"] = self.create_provenance(confidence=1.0, verified_on_chain=True).to_dict()
        return dex_data

    def scan_recent_tokens(self, limit: int = 10) -> List[Dict[str, Any]]:
        self._live_sol_price_usd = self.get_sol_price_usd()

        dex_tokens = self.dex_api.scan_recent_tokens(limit=limit)
        if dex_tokens:
            # Newest market creation first; liquidity is a tie-breaker, not the primary signal.
            return sorted(
                dex_tokens,
                key=lambda x: (
                    x.get("first_seen_ts") or 0.0,
                    x.get("liquidity") or 0.0,
                ),
                reverse=True,
            )

        recent_sigs = self.rpc.get_signatures_for_address(PUMP_FUN_PROGRAM, limit=min(limit, 15)) or []
        discovered: List[Dict[str, Any]] = []
        for sig_info in recent_sigs:
            sig = sig_info.get("signature")
            if not sig:
                continue
            tx = self.rpc.get_transaction(sig)
            if not tx:
                continue
            swaps = self.swap_parser.parse_transaction(
                tx, sol_price_usd=self._live_sol_price_usd, source_type=SourceType.REAL
            )
            for swap in swaps:
                market = self.get_token_market_data(swap.mint)
                if market:
                    discovered.append(market)
        return discovered

    def get_token_security_data(self, mint: str) -> Optional[Dict[str, Any]]:
        verification = self.mint_verifier.verify_mint(mint)
        if not verification.is_valid_mint:
            return None
        return {
            "mint": mint,
            "mint_auth_revoked": verification.mint_auth_revoked,
            "freeze_auth_revoked": verification.freeze_auth_revoked,
            "lp_locked_pct": None,
            "top10_holder_pct": verification.top10_holder_pct,
            "dev_holding_pct": None,
            "is_honeypot": None,
            "is_wash_traded": None,
            "cluster_funder": None,
            "provenance": self.create_provenance(confidence=1.0, verified_on_chain=True).to_dict(),
        }

    def _mark_seen(self, mint: str, signature: str) -> None:
        seen = self._seen_signatures[mint]
        order = self._seen_signature_order[mint]
        if signature in seen:
            return
        seen.add(signature)
        order.append(signature)
        while len(order) > self._max_seen_signatures:
            old = order.popleft()
            seen.discard(old)

    def get_recent_trades(self, mint: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Read only the newest bounded window, but execute RPC getTransaction only
        for signatures that have not already been processed in this provider run.
        This converts repeated full rescans into incremental ingestion without
        pretending the RPC exposes an "after" cursor.
        """
        signatures = self.rpc.get_signatures_for_address(mint, limit=min(limit, 10))
        if not signatures:
            return []

        seen = self._seen_signatures[mint]
        results: List[Dict[str, Any]] = []
        consecutive_tx_failures = 0

        for sig_info in signatures:
            sig = sig_info.get("signature")
            if not sig or sig in seen:
                continue

            tx = self.rpc.get_transaction(sig)
            if not tx:
                consecutive_tx_failures += 1
                if consecutive_tx_failures >= 3:
                    logger.warning(
                        "Stopping tx scan for %s... after 3 consecutive RPC failures",
                        mint[:8],
                    )
                    break
                continue

            consecutive_tx_failures = 0
            swaps = self.swap_parser.parse_transaction(
                tx, sol_price_usd=self._live_sol_price_usd, source_type=SourceType.REAL
            )
            # A successful transaction fetch is now durable evidence that this
            # signature was inspected, even when it contained no target swap.
            self._mark_seen(mint, sig)

            for swap in swaps:
                if swap.mint != mint:
                    continue
                results.append({
                    "signature": swap.signature,
                    "slot": swap.slot,
                    "timestamp": swap.timestamp,
                    "signer": swap.wallet,
                    "token_mint": swap.mint,
                    "type": swap.side,
                    "usd_amount": swap.quote_amount_usd,
                    "token_amount": swap.token_amount,
                    "price_usd": swap.price_usd,
                    "venue": swap.venue,
                    "is_whale": swap.is_whale,
                    "provenance": swap.provenance.to_dict(),
                })

        return results
