"""
Solana Address Validator.
Validates Base58 public keys, checks checksum lengths (32-44 chars),
and identifies known system / program addresses.
"""

import re
from typing import Set

BASE58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
BASE58_REGEX = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$")

KNOWN_SOLANA_SYSTEM_PROGRAMS: Set[str] = {
    "11111111111111111111111111111111",                                # System Program
    "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",                      # SPL Token Program
    "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb",                      # Token-2022 Program
    "So11111111111111111111111111111111111111112",                      # Wrapped SOL (WSOL)
    "SysvarRent111111111111111111111111111111111",                      # Sysvar Rent
    "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8",                      # Raydium AMM V4
    "CPMMoo8L3F4NbTegBCKVNunggL7H1ZpdTHKxQB5qKP1C",                      # Raydium CPMM
    "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P",                      # Pump.fun Program
    "LBUZKhRxPF3XUpBCjp4YzTKgLccjZhTSDM9YuVaPwxo",                      # Meteora DLMM
    "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc"                       # Orca Whirlpool
}


class SolanaAddressValidator:
    @classmethod
    def is_valid_base58_address(cls, address: str) -> bool:
        """Verify that address is a valid Base58 encoded Solana public key."""
        if not address or not isinstance(address, str):
            return False
        if len(address) < 32 or len(address) > 44:
            return False
        return bool(BASE58_REGEX.match(address))

    @classmethod
    def is_known_system_program(cls, address: str) -> bool:
        return address in KNOWN_SOLANA_SYSTEM_PROGRAMS

    @classmethod
    def validate_token_mint(cls, mint: str) -> bool:
        """Strictly validate that mint is a valid Solana public key format and not a system program."""
        if not cls.is_valid_base58_address(mint):
            return False
        if mint in ("11111111111111111111111111111111", "SysvarRent111111111111111111111111111111111"):
            return False
        return True
