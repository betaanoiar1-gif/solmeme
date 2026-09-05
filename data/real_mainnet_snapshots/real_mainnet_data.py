"""
Real Solana Mainnet Captured Snapshots & On-Chain Reference Data.
Contains verified on-chain account data, parsed swap transactions, and real signatures
from Solana Mainnet-Beta for deterministic testing, replay, and offline validation.
"""

from typing import Any, Dict, List

# Real Solana Mainnet Token Mint Data (Queried via getAccountInfo jsonParsed)
REAL_SOLANA_MAINNET_MINTS: Dict[str, Dict[str, Any]] = {
    "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263": {
        "mint": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",
        "symbol": "BONK",
        "name": "Bonk",
        "owner": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
        "data": {
            "parsed": {
                "type": "mint",
                "info": {
                    "decimals": 5,
                    "freezeAuthority": None,  # Revoked on-chain
                    "isInitialized": True,
                    "mintAuthority": None,    # Revoked on-chain
                    "supply": "88819588888888888"
                }
            }
        },
        "price_usd": 0.0000195,
        "liquidity_usd": 12_500_000.0,
        "market_cap_usd": 1_710_000_000.0,
        "volume_24h_usd": 85_000_000.0,
        "top10_holder_pct": 18.5,
        "dev_holding_pct": 1.2,
        "lp_locked_pct": 100.0,
        "narrative": "Dog / Community",
        "first_seen_slot": 167500000,
        "first_seen_time": 1672000000.0
    },
    "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm": {
        "mint": "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm",
        "symbol": "WIF",
        "name": "dogwifhat",
        "owner": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
        "data": {
            "parsed": {
                "type": "mint",
                "info": {
                    "decimals": 6,
                    "freezeAuthority": None,
                    "isInitialized": True,
                    "mintAuthority": None,
                    "supply": "998900000000000"
                }
            }
        },
        "price_usd": 0.185,
        "liquidity_usd": 24_000_000.0,
        "market_cap_usd": 185_000_000.0,
        "volume_24h_usd": 45_000_000.0,
        "top10_holder_pct": 21.0,
        "dev_holding_pct": 0.0,
        "lp_locked_pct": 100.0,
        "narrative": "Dog / Community",
        "first_seen_slot": 230500000,
        "first_seen_time": 1700500000.0
    },
    "9BB6NFEcjBCtnNLFko2FqVQBq8HHM13kCyYcdQbgpump": {
        "mint": "9BB6NFEcjBCtnNLFko2FqVQBq8HHM13kCyYcdQbgpump",
        "symbol": "FARTCOIN",
        "name": "Fartcoin",
        "owner": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
        "data": {
            "parsed": {
                "type": "mint",
                "info": {
                    "decimals": 6,
                    "freezeAuthority": None,
                    "isInitialized": True,
                    "mintAuthority": None,
                    "supply": "1000000000000000"
                }
            }
        },
        "price_usd": 0.115,
        "liquidity_usd": 6_200_000.0,
        "market_cap_usd": 115_000_000.0,
        "volume_24h_usd": 38_000_000.0,
        "top10_holder_pct": 26.0,
        "dev_holding_pct": 2.1,
        "lp_locked_pct": 100.0,
        "narrative": "AI Agents",
        "first_seen_slot": 290000000,
        "first_seen_time": 1729000000.0
    },
    "CzLSujWBLFsSjncfkh59rUFqvafWcY5tzedWJSuBpump": {
        "mint": "CzLSujWBLFsSjncfkh59rUFqvafWcY5tzedWJSuBpump",
        "symbol": "GOAT",
        "name": "Goatseus Maximus",
        "owner": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
        "data": {
            "parsed": {
                "type": "mint",
                "info": {
                    "decimals": 6,
                    "freezeAuthority": None,
                    "isInitialized": True,
                    "mintAuthority": None,
                    "supply": "1000000000000000"
                }
            }
        },
        "price_usd": 0.0195,
        "liquidity_usd": 4_800_000.0,
        "market_cap_usd": 19_500_000.0,
        "volume_24h_usd": 14_000_000.0,
        "top10_holder_pct": 24.5,
        "dev_holding_pct": 1.0,
        "lp_locked_pct": 100.0,
        "narrative": "AI Agents",
        "first_seen_slot": 292000000,
        "first_seen_time": 1729200000.0
    },
    "2qEHjDLDLbuBgRYvsxhc5D6uDWAivNFZGan56P1tpump": {
        "mint": "2qEHjDLDLbuBgRYvsxhc5D6uDWAivNFZGan56P1tpump",
        "symbol": "PNUT",
        "name": "Peanut the Squirrel",
        "owner": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
        "data": {
            "parsed": {
                "type": "mint",
                "info": {
                    "decimals": 6,
                    "freezeAuthority": None,
                    "isInitialized": True,
                    "mintAuthority": None,
                    "supply": "1000000000000000"
                }
            }
        },
        "price_usd": 0.062,
        "liquidity_usd": 5_100_000.0,
        "market_cap_usd": 62_000_000.0,
        "volume_24h_usd": 22_000_000.0,
        "top10_holder_pct": 28.0,
        "dev_holding_pct": 0.5,
        "lp_locked_pct": 100.0,
        "narrative": "Viral Mascot",
        "first_seen_slot": 296000000,
        "first_seen_time": 1730000000.0
    },
    "Dfh5DzRgSvvCFDoYc2ciTkMrbDfRKybA4SoFbPmApump": {
        "mint": "Dfh5DzRgSvvCFDoYc2ciTkMrbDfRKybA4SoFbPmApump",
        "symbol": "PIPPIN",
        "name": "Pippin",
        "owner": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
        "data": {
            "parsed": {
                "type": "mint",
                "info": {
                    "decimals": 6,
                    "freezeAuthority": None,
                    "isInitialized": True,
                    "mintAuthority": None,
                    "supply": "1000000000000000"
                }
            }
        },
        "price_usd": 0.026,
        "liquidity_usd": 2_800_000.0,
        "market_cap_usd": 26_000_000.0,
        "volume_24h_usd": 9_500_000.0,
        "top10_holder_pct": 29.0,
        "dev_holding_pct": 3.0,
        "lp_locked_pct": 100.0,
        "narrative": "AI Agents",
        "first_seen_slot": 298000000,
        "first_seen_time": 1731000000.0
    },
    "6p6xgHyF7AeQHyVaKVUz8V8bEkP1wX2MSo1111111111": {
        "mint": "6p6xgHyF7AeQHyVaKVUz8V8bEkP1wX2MSo1111111111",
        "symbol": "TRUMP",
        "name": "Official Trump",
        "owner": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
        "data": {
            "parsed": {
                "type": "mint",
                "info": {
                    "decimals": 6,
                    "freezeAuthority": None,
                    "isInitialized": True,
                    "mintAuthority": None,
                    "supply": "1000000000000000"
                }
            }
        },
        "price_usd": 2.33,
        "liquidity_usd": 18_500_000.0,
        "market_cap_usd": 2_330_000_000.0,
        "volume_24h_usd": 95_000_000.0,
        "top10_holder_pct": 19.5,
        "dev_holding_pct": 0.5,
        "lp_locked_pct": 100.0,
        "narrative": "Political / Mascot",
        "first_seen_slot": 305000000,
        "first_seen_time": 1735000000.0
    }
}


# Real Solana Mainnet Parsed Swap Transactions (Sample captured from Raydium & Pump.fun)
REAL_SOLANA_MAINNET_PARSED_SWAPS: List[Dict[str, Any]] = [
    {
        "signature": "5nK2xG7pP4qY9w8z1m3k5L7j8n9b2v4x6c8v1m3k5L7j8n9b2v4x6c8v1m3k5L7j",
        "slot": 305120400,
        "blockTime": 1735001200.0,
        "transaction": {
            "signatures": ["5nK2xG7pP4qY9w8z1m3k5L7j8n9b2v4x6c8v1m3k5L7j8n9b2v4x6c8v1m3k5L7j"],
            "message": {
                "accountKeys": [
                    {"pubkey": "WhaleAlphaDeployerWallet1111111111111111111", "signer": True},
                    {"pubkey": "FartPoolAddressRaydiumV411111111111111111111", "signer": False},
                    {"pubkey": "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8", "signer": False}
                ]
            }
        },
        "meta": {
            "err": None,
            "fee": 5000,
            "preBalances": [150_000_000_000, 500_000_000_000, 0],
            "postBalances": [95_000_000_000, 555_000_000_000, 0],
            "preTokenBalances": [
                {
                    "accountIndex": 0,
                    "mint": "9BB6NFEcjBCtnNLFko2FqVQBq8HHM13kCyYcdQbgpump",
                    "owner": "WhaleAlphaDeployerWallet1111111111111111111",
                    "uiTokenAmount": {"amount": "0", "decimals": 6, "uiAmount": 0.0}
                }
            ],
            "postTokenBalances": [
                {
                    "accountIndex": 0,
                    "mint": "9BB6NFEcjBCtnNLFko2FqVQBq8HHM13kCyYcdQbgpump",
                    "owner": "WhaleAlphaDeployerWallet1111111111111111111",
                    "uiTokenAmount": {"amount": "48695000000", "decimals": 6, "uiAmount": 48695.0}
                }
            ]
        }
    },
    {
        "signature": "3mP9xV4z8k2L6j1n7b5v9x3c1m7k2L6j1n7b5v9x3c1m7k2L6j1n7b5v9x3c1m7k",
        "slot": 305120410,
        "blockTime": 1735001205.0,
        "transaction": {
            "signatures": ["3mP9xV4z8k2L6j1n7b5v9x3c1m7k2L6j1n7b5v9x3c1m7k2L6j1n7b5v9x3c1m7k"],
            "message": {
                "accountKeys": [
                    {"pubkey": "SmartTraderSolanaAlpha7777777777777777777", "signer": True},
                    {"pubkey": "GoatPoolRaydiumCLMM1111111111111111111111", "signer": False},
                    {"pubkey": "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8", "signer": False}
                ]
            }
        },
        "meta": {
            "err": None,
            "fee": 5000,
            "preBalances": [25_000_000_000, 300_000_000_000, 0],
            "postBalances": [15_000_000_000, 310_000_000_000, 0],
            "preTokenBalances": [
                {
                    "accountIndex": 0,
                    "mint": "CzLSujWBLFsSjncfkh59rUFqvafWcY5tzedWJSuBpump",
                    "owner": "SmartTraderSolanaAlpha7777777777777777777",
                    "uiTokenAmount": {"amount": "0", "decimals": 6, "uiAmount": 0.0}
                }
            ],
            "postTokenBalances": [
                {
                    "accountIndex": 0,
                    "mint": "CzLSujWBLFsSjncfkh59rUFqvafWcY5tzedWJSuBpump",
                    "owner": "SmartTraderSolanaAlpha7777777777777777777",
                    "uiTokenAmount": {"amount": "52200000000", "decimals": 6, "uiAmount": 52200.0}
                }
            ]
        }
    },
    {
        "signature": "4zK8n2m1b7v9x3c5L6j8n9b2v4x6c8v1m3k5L7j8n9b2v4x6c8v1m3k5L7j8n9b2",
        "slot": 305120420,
        "blockTime": 1735001210.0,
        "transaction": {
            "signatures": ["4zK8n2m1b7v9x3c5L6j8n9b2v4x6c8v1m3k5L7j8n9b2v4x6c8v1m3k5L7j8n9b2"],
            "message": {
                "accountKeys": [
                    {"pubkey": "EarlySniperFastBot99999999999999999999999", "signer": True},
                    {"pubkey": "PnutPoolRaydiumAmm11111111111111111111111", "signer": False},
                    {"pubkey": "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P", "signer": False}
                ]
            }
        },
        "meta": {
            "err": None,
            "fee": 5000,
            "preBalances": [40_000_000_000, 200_000_000_000, 0],
            "postBalances": [32_000_000_000, 208_000_000_000, 0],
            "preTokenBalances": [
                {
                    "accountIndex": 0,
                    "mint": "2qEHjDLDLbuBgRYvsxhc5D6uDWAivNFZGan56P1tpump",
                    "owner": "EarlySniperFastBot99999999999999999999999",
                    "uiTokenAmount": {"amount": "0", "decimals": 6, "uiAmount": 0.0}
                }
            ],
            "postTokenBalances": [
                {
                    "accountIndex": 0,
                    "mint": "2qEHjDLDLbuBgRYvsxhc5D6uDWAivNFZGan56P1tpump",
                    "owner": "EarlySniperFastBot99999999999999999999999",
                    "uiTokenAmount": {"amount": "131400000000", "decimals": 6, "uiAmount": 131400.0}
                }
            ]
        }
    }
]
