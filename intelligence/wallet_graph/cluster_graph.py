"""
Wallet Cluster Graph Engine.
Discovers shared funding, coordinated entry/exit groups,
and computes cluster-adjusted independent signals.
"""

from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Set, Optional


@dataclass
class ClusterAnalysisResult:
    total_wallets: int
    independent_clusters: int
    cluster_discount_factor: float  # 0.1 (all coordinated) to 1.0 (fully independent)
    suspicious_clusters_found: int
    insider_like_probability: float  # 0 to 100


class WalletClusterGraph:
    def __init__(self):
        self._funding_graph: Dict[str, Set[str]] = defaultdict(set)  # funder -> funded_wallets
        self._wallet_funder: Dict[str, str] = {}

    def register_funding(self, funder_address: str, target_wallet: str):
        self._funding_graph[funder_address].add(target_wallet)
        self._wallet_funder[target_wallet] = funder_address

    def analyze_token_wallets(self, wallets: List[str], creator_address: Optional[str] = None) -> ClusterAnalysisResult:
        if not wallets:
            return ClusterAnalysisResult(
                total_wallets=0,
                independent_clusters=0,
                cluster_discount_factor=1.0,
                suspicious_clusters_found=0,
                insider_like_probability=0.0
            )

        unique_wallets = list(set(wallets))
        cluster_map: Dict[str, List[str]] = defaultdict(list)
        unclustered_count = 0
        creator_linked_count = 0

        for w in unique_wallets:
            funder = self._wallet_funder.get(w)
            if funder:
                cluster_map[funder].append(w)
                if creator_address and funder == creator_address:
                    creator_linked_count += 1
            else:
                unclustered_count += 1

        suspicious_clusters = sum(1 for f, members in cluster_map.items() if len(members) >= 2)
        total_clusters = unclustered_count + len(cluster_map)

        # Discount factor
        discount = total_clusters / max(len(unique_wallets), 1)

        # Insider probability calculation
        insider_prob = 0.0
        if creator_linked_count > 0:
            insider_prob += min((creator_linked_count / len(unique_wallets)) * 100.0 + 30.0, 100.0)
        if suspicious_clusters > 0:
            insider_prob += min(suspicious_clusters * 20.0, 60.0)

        insider_prob = min(max(insider_prob, 0.0), 100.0)

        return ClusterAnalysisResult(
            total_wallets=len(unique_wallets),
            independent_clusters=total_clusters,
            cluster_discount_factor=round(discount, 3),
            suspicious_clusters_found=suspicious_clusters,
            insider_like_probability=round(insider_prob, 2)
        )
