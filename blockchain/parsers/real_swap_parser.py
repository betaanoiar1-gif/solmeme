"""
Real Solana DEX Swap & Transaction Parser.
Decodes on-chain parsed transactions and calculates exact token and SOL balance deltas
to extract real swaps across Raydium, Pump.fun, Meteora, Orca, and Jupiter.
Zero placeholder quotes. If quote cannot be determined, USD value is None (UNKNOWN).
"""

from dataclasses import dataclass, field
import logging
import time
from typing import Any, Dict, List, Optional

from blockchain.parsers.dex_pool_adapter import DexPoolAdapter
from blockchain.solana.types import Provenance, SourceType

logger = logging.getLogger("meme_alpha_hunter.swap_parser")

SOL_MINT = "So11111111111111111111111111111111111111112"
USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
USDT_MINT = "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB"


@dataclass
class RealSwapRecord:
    signature: str
    slot: int
    timestamp: Optional[float]
    pool: str
    mint: str
    symbol: Optional[str]
    wallet: str  # Signer
    side: str  # "BUY" or "SELL"
    token_amount: float
    quote_amount_sol: Optional[float]
    quote_amount_usd: Optional[float]
    price_usd: Optional[float]
    venue: str  # "Raydium_AMM_V4", "Pump.fun", "Meteora_DLMM", "Raydium_CPMM", "Jupiter", "DEX_AMM"
    is_whale: bool = False
    is_quote_verified: bool = False
    provenance: Provenance = field(default_factory=Provenance)


class RealSwapParser:
    @classmethod
    def parse_transaction(
        cls,
        tx_data: Dict[str, Any],
        sol_price_usd: Optional[float] = None,
        target_mint: Optional[str] = None,
        source_type: SourceType = SourceType.REAL
    ) -> List[RealSwapRecord]:
        """
        Parses a Solana getParsedTransaction or getTransaction JSON object.
        Uses universal on-chain token balance deltas (preTokenBalances vs postTokenBalances)
        and SOL balance deltas (preBalances vs postBalances) to extract verified swaps.
        """
        meta = tx_data.get("meta")
        if not meta or meta.get("err") is not None:
            return []  # Skip failed transactions

        tx = tx_data.get("transaction", {})
        signatures = tx.get("signatures", [])
        signature = signatures[0] if signatures else tx_data.get("signature", "unknown_tx")

        slot = int(tx_data.get("slot", 0))
        raw_block_time = tx_data.get("blockTime")
        block_time = float(raw_block_time) if raw_block_time is not None else None

        # Determine signer (primary wallet)
        message = tx.get("message", {})
        account_keys = message.get("accountKeys", [])
        if not account_keys:
            return []

        signer = None
        for ak in account_keys:
            if isinstance(ak, dict):
                pubkey = ak.get("pubkey", "")
                if ak.get("signer", False) and signer is None:
                    signer = pubkey
            else:
                signer = str(ak)
                break

        if not signer:
            return []

        # Identify pool via DEX adapter
        pool_info = DexPoolAdapter.identify_pool_from_tx(tx_data)
        pool_address = pool_info.pool_address if pool_info else "UnknownPool"
        venue = pool_info.venue_name if pool_info else "DEX_AMM"

        # Extract pre and post token balances
        pre_token_balances = meta.get("preTokenBalances", [])
        post_token_balances = meta.get("postTokenBalances", [])

        # Build mapping of (owner:mint) -> balance
        pre_map: Dict[str, float] = {}
        post_map: Dict[str, float] = {}

        for b in pre_token_balances:
            m = b.get("mint", "")
            owner = b.get("owner", "")
            ui_amt = float(b.get("uiTokenAmount", {}).get("uiAmount", 0.0) or 0.0)
            key = f"{owner}:{m}"
            pre_map[key] = ui_amt

        for b in post_token_balances:
            m = b.get("mint", "")
            owner = b.get("owner", "")
            ui_amt = float(b.get("uiTokenAmount", {}).get("uiAmount", 0.0) or 0.0)
            key = f"{owner}:{m}"
            post_map[key] = ui_amt

        # Calculate exact SOL delta for signer (in SOL)
        pre_sol_lamports = meta.get("preBalances", [0])[0] if meta.get("preBalances") else 0
        post_sol_lamports = meta.get("postBalances", [0])[0] if meta.get("postBalances") else 0
        fee_lamports = meta.get("fee", 5000)

        # Net SOL change for signer
        sol_delta = ((post_sol_lamports + fee_lamports) - pre_sol_lamports) / 1e9

        swaps: List[RealSwapRecord] = []
        all_mints = set([b.get("mint") for b in pre_token_balances + post_token_balances if b.get("mint")])
        quote_mints = {SOL_MINT, USDC_MINT, USDT_MINT}

        for mint in all_mints:
            if mint in quote_mints:
                continue
            if target_mint and mint != target_mint:
                continue

            signer_key = f"{signer}:{mint}"
            pre_amt = pre_map.get(signer_key, 0.0)
            post_amt = post_map.get(signer_key, 0.0)
            token_delta = post_amt - pre_amt

            if abs(token_delta) < 1e-6:
                continue

            # Determine side & quote amounts
            if token_delta > 0:
                side = "BUY"
                token_amount = token_delta
                sol_spent = abs(sol_delta) if sol_delta < 0 else None
            else:
                side = "SELL"
                token_amount = abs(token_delta)
                sol_spent = sol_delta if sol_delta > 0 else None

            # Calculate verifiable USD value
            quote_sol = sol_spent
            quote_usd = None
            price_usd = None
            is_quote_verified = False

            if quote_sol is not None and sol_price_usd is not None and sol_price_usd > 0:
                quote_usd = round(quote_sol * sol_price_usd, 4)
                if token_amount > 0:
                    price_usd = quote_usd / token_amount
                is_quote_verified = (source_type == SourceType.REAL)

            is_whale = bool(is_quote_verified and quote_usd is not None and quote_usd >= 5000.0)

            record = RealSwapRecord(
                signature=signature,
                slot=slot,
                timestamp=block_time,
                pool=pool_address,
                mint=mint,
                symbol=None,
                wallet=signer,
                side=side,
                token_amount=token_amount,
                quote_amount_sol=quote_sol,
                quote_amount_usd=quote_usd,
                price_usd=price_usd,
                venue=venue,
                is_whale=is_whale,
                is_quote_verified=is_quote_verified,
                provenance=Provenance(
                    source_type=source_type,
                    provider=f"SolanaRPC.{venue}",
                    timestamp=block_time,
                    observed_at=time.time(),
                    slot=slot,
                    signature=signature,
                    confidence=1.0 if is_quote_verified else 0.5,
                    verified_on_chain=True
                )
            )
            swaps.append(record)

        return swaps
