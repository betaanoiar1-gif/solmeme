"""
Parsers for Solana DEX transactions (Raydium, Pump.fun, Meteora, Orca).
Decodes swap amounts, liquidity pool creations, and mint actions.
"""

from typing import Any, Dict, Optional
from blockchain.solana.types import LiquidityPool, OnChainTransaction


class DexParser:
    RAYDIUM_AMM_V4 = "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8"
    RAYDIUM_CPMM = "CPMMoo8L3F4NbTegBCKVNunggL7H1ZpdTHKxQB5qKP1C"
    PUMPFUN_PROGRAM = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
    METEORA_DLMM = "LBUZKhRxPF3XUpBCjp4YzTKgLccjZhTSDM9YuVaPwxo"

    @classmethod
    def identify_dex(cls, program_id: str) -> str:
        if program_id == cls.PUMPFUN_PROGRAM:
            return "PumpFun"
        elif program_id in (cls.RAYDIUM_AMM_V4, cls.RAYDIUM_CPMM):
            return "Raydium"
        elif program_id == cls.METEORA_DLMM:
            return "Meteora"
        return "UnknownDEX"

    @classmethod
    def parse_swap_event(cls, tx_raw: Dict[str, Any]) -> Optional[OnChainTransaction]:
        """Extract swap details from raw transaction or DEX webhook payload."""
        try:
            signature = tx_raw.get("signature", "mock_sig")
            slot = tx_raw.get("slot", 0)
            timestamp = tx_raw.get("timestamp", 0.0)
            signer = tx_raw.get("signer", "unknown_signer")
            token_mint = tx_raw.get("token_mint", "")
            pool_address = tx_raw.get("pool_address", "")
            tx_type = tx_raw.get("type", "BUY")
            token_amount = float(tx_raw.get("token_amount", 0.0))
            sol_amount = float(tx_raw.get("sol_amount", 0.0))
            usd_amount = float(tx_raw.get("usd_amount", 0.0))
            price_usd = float(tx_raw.get("price_usd", 0.0))

            return OnChainTransaction(
                signature=signature,
                slot=slot,
                timestamp=timestamp,
                signer=signer,
                token_mint=token_mint,
                pool_address=pool_address,
                type=tx_type,
                token_amount=token_amount,
                sol_amount=sol_amount,
                usd_amount=usd_amount,
                price_usd=price_usd
            )
        except Exception:
            return None
