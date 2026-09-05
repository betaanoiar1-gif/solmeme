"""
Network Connectivity and Solana Mainnet RPC Prober.
Tests getHealth, getSlot, getLatestBlockhash, getAccountInfo, getSignaturesForAddress.
Outputs real latency, endpoint status, and verification metrics.
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request

# Ensure root on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from blockchain.rpc.rpc_client import SolanaRPCClient
from data.ingestion.dex_provider import DexPublicProvider


def probe_network():
    print("============================================================")
    print("PHASE 1: RUNTIME ENVIRONMENT & NETWORK CONNECTIVITY")
    print("============================================================")
    print(f"Python Version: {sys.version.split()[0]}")
    print(f"Operating System: {sys.platform}")

import json
import os
import socket
import sys
import time
import urllib.error
import urllib.request

# Ensure root on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from blockchain.rpc.rpc_client import SolanaRPCClient
from data.ingestion.dex_provider import DexPublicProvider


def probe_network():
    print("============================================================")
    print("PHASE 1: RUNTIME ENVIRONMENT & NETWORK CONNECTIVITY")
    print("============================================================")
    print(f"Python Version: {sys.version.split()[0]}")
    print(f"Operating System: {sys.platform}")

    # 1. DNS Resolution Test
    dns_resolved = False
    dns_ip = "UNKNOWN"
    try:
        dns_ip = socket.gethostbyname("api.mainnet-beta.solana.com")
        dns_resolved = True
        print(f"✅ 1. DNS Resolution: SUCCESS (api.mainnet-beta.solana.com -> {dns_ip})")
    except Exception as e:
        print(f"❌ 1. DNS Resolution: FAILED ({e})")

    # 2. HTTPS Connectivity Test
    https_connected = False
    public_ip = "UNKNOWN"
    try:
        req = urllib.request.Request("https://api.ipify.org?format=json", headers={"User-Agent": "MemeHunter/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            public_ip = data.get("ip", "UNKNOWN")
            https_connected = True
            print(f"✅ 2. HTTPS Connectivity: SUCCESS (Public IP: {public_ip})")
    except Exception as e:
        print(f"❌ 2. HTTPS Connectivity: FAILED ({e})")

    print(f"Runtime Environment: {'GitHub Actions / Cloud Runner' if 'GITHUB_ACTIONS' in os.environ else 'Arena.ai Workspace Container'}")
    print("============================================================\n")

    # 3. Solana RPC Connectivity & 4. JSON-RPC Request
    print("============================================================")
    print("PHASE 2: SOLANA MAINNET RPC DIRECT PROBE")
    print("============================================================")

    rpc = SolanaRPCClient()
    successful_calls = 0
    total_calls = 0

    methods_to_test = [
        ("getHealth", []),
        ("getSlot", []),
        ("getLatestBlockhash", []),
        ("getAccountInfo", ["TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA", {"encoding": "jsonParsed"}]),
        ("getSignaturesForAddress", ["675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8", {"limit": 5}]) # Raydium AMM V4
    ]

    for method, params in methods_to_test:
        total_calls += 1
        t0 = time.time()
        res = rpc.call(method, params, use_cache=False)
        latency_ms = (time.time() - t0) * 1000.0
        ts = time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())

        if res is not None:
            successful_calls += 1
            print(f"[{ts}] ✅ {method:<26} | Latency: {latency_ms:>6.1f}ms | Result: {str(res)[:60]}...")
        else:
            print(f"[{ts}] ❌ {method:<26} | Latency: {latency_ms:>6.1f}ms | FAILED / UNAVAILABLE")

    print("------------------------------------------------------------")
    print(f"Total RPC Calls: {total_calls} | Successful: {successful_calls} | Failed: {total_calls - successful_calls}")
    metrics = rpc.get_health_metrics()
    for ep, m in metrics.items():
        print(f"  • {ep} -> Total: {m['total_requests']}, Succ: {m['successful_requests']}, Active: {m['is_active']}")
    print("============================================================\n")

    # 5. DEX Public API Probe
    dex = DexPublicProvider()
    print("============================================================")
    print("PHASE 3: DEX PUBLIC API PROBE")
    print("============================================================")
    wsol_meta = dex.get_token_metadata("So11111111111111111111111111111111111111112")
    if wsol_meta:
        print(f"✅ 5. DEX Public API: SUCCESS | Metadata retrieved for WSOL: {wsol_meta.get('name')}")
    else:
        print("❌ 5. DEX Public API: OFFLINE / UNAVAILABLE")
    print("============================================================\n")

    return successful_calls > 0

    return successful_calls > 0


if __name__ == "__main__":
    success = probe_network()
    # Exit with 0 so workflow can proceed to run engine
    sys.exit(0)
