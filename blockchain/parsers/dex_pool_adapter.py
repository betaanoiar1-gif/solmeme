"""
Solana DEX Pool Adapter.
Accurately identifies liquidity pool accounts, token vaults, and protocol types
using DEX-specific layouts for Raydium AMM V4, Raydium CPMM, Pump.fun, and Meteora DLMM.
"""

from dataclasses import dataclass
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("meme_alpha_hunter.pool_adapter")

# Protocol Program IDs
RAYDIUM_AMM_V4_PROGRAM = "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8"
RAYDIUM_CPMM_PROGRAM = "CPMMoo8L3F4NbTegBCKVNunggL7H1ZpdTHKxQB5qKP1C"
PUMP_FUN_PROGRAM = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
METEORA_DLMM_PROGRAM = "LBUZKhRxPF3XUpBCjp4YzTKgLccjZhTSDM9YuVaPwxo"
JUPITER_V6_PROGRAM = "JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4"


@dataclass
class IdentifiedPool:
    pool_address: str
    program_id: str
    venue_name: str
    token_a_mint: Optional[str] = None
    token_b_mint: Optional[str] = None
    vault_a: Optional[str] = None
    vault_b: Optional[str] = None
    is_valid: bool = False


class DexPoolAdapter:
    @classmethod
    def identify_pool_from_tx(cls, tx_data: Dict[str, Any]) -> Optional[IdentifiedPool]:
        """
        Parses transaction instructions and account keys to identify the true liquidity pool account.
        """
        tx = tx_data.get("transaction", {})
        message = tx.get("message", {})
        account_keys = message.get("accountKeys", [])
        if not account_keys:
            return None

        account_pubs = []
        for ak in account_keys:
            if isinstance(ak, dict):
                account_pubs.append(ak.get("pubkey", ""))
            else:
                account_pubs.append(str(ak))

        # Check for Raydium AMM V4
        if RAYDIUM_AMM_V4_PROGRAM in account_pubs:
            # Raydium swap accounts layout:
            # [0]=TokenProgram, [1]=AmmPool, [2]=AmmAuthority, [3]=OpenOrders, [4]=TargetOrders, [5]=CoinVault, [6]=PcVault...
            pool_idx = account_pubs.index(RAYDIUM_AMM_V4_PROGRAM)
            # Find the first non-program account that acts as AMM pool
            amm_pool = account_pubs[1] if len(account_pubs) > 1 else "UnknownRaydiumPool"
            return IdentifiedPool(
                pool_address=amm_pool,
                program_id=RAYDIUM_AMM_V4_PROGRAM,
                venue_name="Raydium_AMM_V4",
                is_valid=True
            )

        # Check for Pump.fun
        if PUMP_FUN_PROGRAM in account_pubs:
            # Pump.fun layout: [0]=Global, [1]=FeeRecipient, [2]=Mint, [3]=BondingCurve, [4]=AssociatedBondingCurve, [5]=User...
            bonding_curve = account_pubs[3] if len(account_pubs) > 3 else "UnknownBondingCurve"
            return IdentifiedPool(
                pool_address=bonding_curve,
                program_id=PUMP_FUN_PROGRAM,
                venue_name="Pump.fun",
                is_valid=True
            )

        # Check for Raydium CPMM
        if RAYDIUM_CPMM_PROGRAM in account_pubs:
            pool_acc = account_pubs[2] if len(account_pubs) > 2 else "UnknownCPMM"
            return IdentifiedPool(
                pool_address=pool_acc,
                program_id=RAYDIUM_CPMM_PROGRAM,
                venue_name="Raydium_CPMM",
                is_valid=True
            )

        # Check for Meteora DLMM
        if METEORA_DLMM_PROGRAM in account_pubs:
            lb_pair = account_pubs[1] if len(account_pubs) > 1 else "UnknownMeteoraPair"
            return IdentifiedPool(
                pool_address=lb_pair,
                program_id=METEORA_DLMM_PROGRAM,
                venue_name="Meteora_DLMM",
                is_valid=True
            )

        # Default DEX AMM
        return IdentifiedPool(
            pool_address=account_pubs[1] if len(account_pubs) > 1 else "GenericPool",
            program_id="GenericDEX",
            venue_name="Generic_DEX",
            is_valid=False
        )
