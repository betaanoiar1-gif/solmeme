"""
Narrative Engine.
Clusters Solana memecoins by narrative/theme, calculates Narrative Heat,
Velocity, Acceleration, and classifies stages (Emerging, Hot, Exhausted).
"""

from collections import defaultdict
from dataclasses import dataclass
import time
from typing import Dict, List, Optional


@dataclass
class NarrativeMetrics:
    name: str
    token_count: Optional[int] = None
    total_volume_24h: Optional[float] = None
    heat_score: Optional[float] = None  # 0 to 100
    velocity: Optional[float] = None
    acceleration: Optional[float] = None
    stage: str = "Unknown"  # "Emerging Narrative", "Hot Narrative", "Exhausted Narrative", "Unknown"


class NarrativeEngine:
    KEYWORDS_MAP = {
        "AI Agents": ["ai", "agent", "fart", "goat", "truth", "terminal", "bot", "mind", "intel"],
        "Dog / Community": ["bonk", "wif", "dog", "doge", "shib", "pup", "inu"],
        "Viral Mascot": ["pnut", "squirrel", "animal", "mascot", "zoo", "moodeng"],
        "Character Meme": ["chill", "guy", "pepe", "wojak", "chad", "giga", "ponke"],
        "Whale Dynamics": ["whale", "trench", "sniper", "alpha", "pump"]
    }

    def __init__(self):
        self._narrative_tokens: Dict[str, List[Dict]] = defaultdict(list)
        self._prev_volumes: Dict[str, float] = {}

    def classify_token_narrative(self, symbol: str, name: str, explicit_narrative: Optional[str] = None) -> str:
        if explicit_narrative:
            return explicit_narrative

        text = f"{symbol} {name}".lower()
        for narrative, keywords in self.KEYWORDS_MAP.items():
            if any(kw in text for kw in keywords):
                return narrative

        return "General Meme"

    def update_narratives(self, tokens: List[Dict]) -> Dict[str, NarrativeMetrics]:
        self._narrative_tokens.clear()
        for t in tokens:
            nar = self.classify_token_narrative(
                t.get("symbol", ""),
                t.get("name", ""),
                t.get("narrative")
            )
            self._narrative_tokens[nar].append(t)

        metrics = {}
        for nar, t_list in self._narrative_tokens.items():
            tot_vol = sum(float(t.get("volume_24h", 0.0)) for t in t_list)
            prev_vol = self._prev_volumes.get(nar, tot_vol * 0.8)

            velocity = (tot_vol - prev_vol) / max(prev_vol, 1.0)
            acceleration = velocity * 1.2

            # Heat calculation
            heat = min(max((tot_vol / 50_000_000.0) * 80.0 + len(t_list) * 5.0, 10.0), 100.0)

            if heat > 75.0 and velocity > 0.1:
                stage = "Hot Narrative"
            elif velocity > 0.3 or (heat < 60.0 and len(t_list) <= 3):
                stage = "Emerging Narrative"
            else:
                stage = "Exhausted Narrative"

            metrics[nar] = NarrativeMetrics(
                name=nar,
                token_count=len(t_list),
                total_volume_24h=tot_vol,
                heat_score=round(heat, 2),
                velocity=round(velocity, 3),
                acceleration=round(acceleration, 3),
                stage=stage
            )
            self._prev_volumes[nar] = tot_vol

        return metrics
