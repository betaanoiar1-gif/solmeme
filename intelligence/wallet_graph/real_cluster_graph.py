"""
Real On-Chain Wallet Relationship Graph and Sybil Cluster Detector.
Analyzes on-chain transfers and transaction co-occurrences to detect:
- FUNDING_LINK (wallet A funded wallet B)
- COMMON_FUNDER (multiple buyer wallets funded by same master wallet)
- TIMING_CORRELATION (wallets transacting in the same slot/second)
- CREATOR_LINK (wallets linked to token deployer)
Distinguishes INDEPENDENT, RELATED, and SYBIL_CLUSTER networks.
"""

from dataclasses import dataclass, field
import logging
import time
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("meme_alpha_hunter.cluster_graph")


@dataclass
class WalletLink:
    source_wallet: str
    target_wallet: str
    link_type: str  # "SOL_FUNDING", "TIMING_CORRELATION", "CREATOR_TRANSFER", "CO_TRADING"
    weight: float
    observed_slot: Optional[int] = None
    signature: Optional[str] = None
    timestamp: float = field(default_factory=time.time)


@dataclass
class ClusterAnalysisResult:
    mint: str
    cluster_id: str
    classification: str  # "INDEPENDENT_WALLETS", "RELATED_WALLETS", "SYBIL_CLUSTER"
    risk_multiplier: float  # 1.0 (safe) to 3.0 (high rug risk)
    total_wallets_analyzed: int
    clustered_wallets_count: int
    cluster_share_of_volume_pct: float
    detected_links: List[WalletLink]
    reasons: List[str]


class RealClusterGraph:
    def __init__(self):
        self.links: List[WalletLink] = []
        self._wallet_slots: Dict[str, Set[int]] = {}  # slot -> set of buyer wallets
        self._funder_map: Dict[str, str] = {}         # wallet -> funder_wallet
        self._creator_map: Dict[str, str] = {}        # mint -> creator_wallet

    def register_transfer(self, from_wallet: str, to_wallet: str, amount_sol: float, signature: str, slot: int, block_time: float):
        """Records an on-chain SOL transfer link between wallets."""
        if from_wallet == to_wallet or not from_wallet or not to_wallet:
            return

        self._funder_map[to_wallet] = from_wallet
        self.links.append(WalletLink(
            source_wallet=from_wallet,
            target_wallet=to_wallet,
            link_type="SOL_FUNDING",
            weight=min(amount_sol * 10.0, 100.0),
            observed_slot=slot,
            signature=signature,
            timestamp=block_time
        ))

    def register_creator(self, mint: str, creator_wallet: str):
        """Records token deployer address."""
        self._creator_map[mint] = creator_wallet

    def register_trade_timing(self, wallet: str, mint: str, slot: int, timestamp: float, signature: str):
        """Records trade slot for timing correlation analysis."""
        if slot not in self._wallet_slots:
            self._wallet_slots[slot] = set()
        self._wallet_slots[slot].add(wallet)

    def analyze_token_wallets(self, mint: str, observed_wallets: List[str], wallet_volumes: Dict[str, float]) -> ClusterAnalysisResult:
        """
        Analyzes observed buyer wallets for a token to determine if trading is organic or sybil/clustered.
        """
        if not observed_wallets:
            return ClusterAnalysisResult(
                mint=mint,
                cluster_id="NONE",
                classification="INDEPENDENT_WALLETS",
                risk_multiplier=1.0,
                total_wallets_analyzed=0,
                clustered_wallets_count=0,
                cluster_share_of_volume_pct=0.0,
                detected_links=[],
                reasons=["No buyer wallets to analyze"]
            )

        creator = self._creator_map.get(mint)
        links_found: List[WalletLink] = []
        reasons: List[str] = []
        clustered_wallets: Set[str] = set()

        # 1. Common funder check
        funder_groups: Dict[str, List[str]] = {}
        for w in observed_wallets:
            funder = self._funder_map.get(w)
            if funder:
                if funder not in funder_groups:
                    funder_groups[funder] = []
                funder_groups[funder].append(w)

        for funder, funded_wallets in funder_groups.items():
            if len(funded_wallets) >= 2:
                reasons.append(f"Common funder {funder[:6]}... funded {len(funded_wallets)} buyer wallets")
                for fw in funded_wallets:
                    clustered_wallets.add(fw)
                    links_found.append(WalletLink(
                        source_wallet=funder,
                        target_wallet=fw,
                        link_type="COMMON_FUNDER",
                        weight=80.0
                    ))

        # 2. Creator linkage check
        if creator:
            for w in observed_wallets:
                if w == creator or self._funder_map.get(w) == creator:
                    clustered_wallets.add(w)
                    reasons.append(f"Buyer wallet {w[:6]}... is funded by or linked to creator {creator[:6]}...")
                    links_found.append(WalletLink(
                        source_wallet=creator,
                        target_wallet=w,
                        link_type="CREATOR_TRANSFER",
                        weight=95.0
                    ))

        # 3. Timing correlation check (same slot sniper bundle)
        for slot, slot_wallets in self._wallet_slots.items():
            overlap = [w for w in slot_wallets if w in observed_wallets]
            if len(overlap) >= 3:
                reasons.append(f"Same-slot timing correlation: {len(overlap)} wallets bought in slot {slot}")
                for ow in overlap:
                    clustered_wallets.add(ow)

        # 4. Compute cluster volume concentration
        total_vol = sum(wallet_volumes.values()) or 1.0
        cluster_vol = sum(wallet_volumes.get(w, 0.0) for w in clustered_wallets)
        cluster_vol_pct = (cluster_vol / total_vol) * 100.0

        total_wallets = len(observed_wallets)
        cluster_count = len(clustered_wallets)

        # Classification
        if cluster_vol_pct >= 40.0 or cluster_count >= (total_wallets * 0.40):
            classification = "SYBIL_CLUSTER"
            risk_multiplier = 2.5
        elif cluster_count >= 2 or cluster_vol_pct >= 20.0:
            classification = "RELATED_WALLETS"
            risk_multiplier = 1.5
        else:
            classification = "INDEPENDENT_WALLETS"
            risk_multiplier = 1.0

        return ClusterAnalysisResult(
            mint=mint,
            cluster_id=f"cluster_{mint[:6]}",
            classification=classification,
            risk_multiplier=risk_multiplier,
            total_wallets_analyzed=total_wallets,
            clustered_wallets_count=cluster_count,
            cluster_share_of_volume_pct=round(cluster_vol_pct, 2),
            detected_links=links_found,
            reasons=reasons or ["Organic distributed wallet participation"]
        )
