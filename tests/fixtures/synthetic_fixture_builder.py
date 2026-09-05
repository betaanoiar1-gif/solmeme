"""
Synthetic Test Fixture Builder (Isolated Testing Only).
Tagged strictly with source_type=REPLAY or source_type=TEST.
Never used in live production and never written to canonical live DB.
"""

import hashlib
import os
import sqlite3
import time
from typing import Any, Dict, List, Tuple

BASE58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def b58encode(b: bytes) -> str:
    n = int.from_bytes(b, "big")
    chars = []
    while n > 0:
        n, r = divmod(n, 58)
        chars.append(BASE58_ALPHABET[r])
    chars.reverse()
    pad = 0
    for byte in b:
        if byte == 0:
            pad += 1
        else:
            break
    return (BASE58_ALPHABET[0] * pad) + "".join(chars)


def b58decode(s: str) -> bytes:
    n = 0
    for char in s:
        idx = BASE58_ALPHABET.find(char)
        if idx == -1:
            raise ValueError(f"Invalid Base58 char: {char}")
        n = n * 58 + idx
    res = []
    while n > 0:
        res.append(n & 0xFF)
        n >>= 8
    res.reverse()
    pad = 0
    for char in s:
        if char == BASE58_ALPHABET[0]:
            pad += 1
        else:
            break
    return (b"\x00" * pad) + bytes(res)


def create_test_fixture_db(target_db_path: str, source_type: str = "REPLAY") -> str:
    """
    Creates an isolated test database with fixture data labeled REPLAY or TEST.
    Never labels test fixtures as REAL.
    """
    assert source_type in ("REPLAY", "SNAPSHOT", "TEST"), "Test fixtures must not use source_type=REAL"

    os.makedirs(os.path.dirname(os.path.abspath(target_db_path)), exist_ok=True)
    conn = sqlite3.connect(target_db_path)
    cursor = conn.cursor()

    cursor.execute("DROP TABLE IF EXISTS live_swaps")
    cursor.execute("""
    CREATE TABLE live_swaps (
        signature TEXT PRIMARY KEY,
        slot INTEGER NOT NULL,
        block_time REAL NOT NULL,
        mint TEXT NOT NULL,
        wallet_pubkey TEXT NOT NULL,
        pool TEXT NOT NULL,
        venue TEXT NOT NULL,
        side TEXT NOT NULL,
        token_amount REAL NOT NULL,
        quote_sol REAL NOT NULL,
        quote_usd REAL NOT NULL,
        price_usd REAL NOT NULL,
        source_type TEXT NOT NULL,
        rpc_verified INTEGER NOT NULL,
        observed_at REAL NOT NULL
    )
    """)

    cursor.execute("DROP TABLE IF EXISTS tokens")
    cursor.execute("""
    CREATE TABLE tokens (
        mint TEXT PRIMARY KEY,
        symbol TEXT NOT NULL,
        name TEXT NOT NULL,
        decimals INTEGER NOT NULL,
        supply REAL NOT NULL,
        price_usd REAL NOT NULL,
        liquidity_usd REAL NOT NULL,
        owner_program TEXT NOT NULL,
        mint_auth_revoked INTEGER NOT NULL,
        freeze_auth_revoked INTEGER NOT NULL,
        top10_holder_pct REAL NOT NULL,
        verification_status TEXT NOT NULL,
        source_type TEXT NOT NULL,
        pool_created_at REAL
    )
    """)

    base_time = 1788623000.0

    tokens_data = [
        {"mint": "9BB6NFEcjBCtnNLFko2FqVQBq8HHM13kCyYcdQbgpump", "symbol": "FARTCOIN", "name": "Fartcoin", "decimals": 6, "supply": 1000000000.0, "price": 0.115, "liq": 3400000.0, "mint_auth": None, "freeze_auth": None, "top10": 26.0, "venue": "Pump.fun", "pool_created_at": base_time - (12000 * 60)},
        {"mint": "CzLSujWBLFsSjncfkh59rUFqvafWcY5tzedWJSuBpump", "symbol": "GOAT", "name": "Goatseus Maximus", "decimals": 6, "supply": 1000000000.0, "price": 0.0195, "liq": 2100000.0, "mint_auth": None, "freeze_auth": None, "top10": 24.5, "venue": "Pump.fun", "pool_created_at": base_time - (9500 * 60)},
        {"mint": "2qEHjDLDLbuBgRYvsxhc5D6uDWAivNFZGan56P1tpump", "symbol": "PNUT", "name": "Peanut the Squirrel", "decimals": 6, "supply": 1000000000.0, "price": 0.062, "liq": 1650000.0, "mint_auth": None, "freeze_auth": None, "top10": 28.0, "venue": "Pump.fun", "pool_created_at": base_time - (7800 * 60)}
    ]

    for t in tokens_data:
        cursor.execute("""
        INSERT INTO tokens VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            t["mint"], t["symbol"], t["name"], t["decimals"], t["supply"],
            t["price"], t["liq"], "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
            1 if t["mint_auth"] is None else 0,
            1 if t["freeze_auth"] is None else 0,
            t["top10"], "VERIFIED_ON_CHAIN", source_type,
            t["pool_created_at"]
        ))

    conn.commit()
    conn.close()
    return target_db_path
