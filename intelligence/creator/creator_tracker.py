"""
Creator Reputation and Previous Behavior Tracker.
Tracks dev deployment history, rug history, and dumps.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class CreatorProfile:
    address: str
    tokens_created: int
    rugged_tokens_count: int
    successful_tokens_count: int
    reputation_score: float  # 0 to 100 (100 = spotless)
    is_blacklisted: bool


class CreatorTracker:
    def __init__(self):
        self._creators: Dict[str, CreatorProfile] = {}
        self._init_known()

    def _init_known(self):
        self._creators["ScammerDev1111111111111111111111111111111"] = CreatorProfile(
            address="ScammerDev1111111111111111111111111111111",
            tokens_created=8,
            rugged_tokens_count=7,
            successful_tokens_count=0,
            reputation_score=0.0,
            is_blacklisted=True
        )
        self._creators["BonkDevGov11111111111111111111111111111111"] = CreatorProfile(
            address="BonkDevGov11111111111111111111111111111111",
            tokens_created=3,
            rugged_tokens_count=0,
            successful_tokens_count=3,
            reputation_score=98.0,
            is_blacklisted=False
        )

    def get_creator_reputation(self, address: str) -> CreatorProfile:
        if address in self._creators:
            return self._creators[address]

        # Unknown creator default
        profile = CreatorProfile(
            address=address,
            tokens_created=1,
            rugged_tokens_count=0,
            successful_tokens_count=0,
            reputation_score=60.0,
            is_blacklisted=False
        )
        self._creators[address] = profile
        return profile
