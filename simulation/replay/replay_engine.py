"""
Point-in-Time Replay Engine.
Replays historical market ticks with strictly zero future data leakage.
"""

from typing import Any, Callable, Dict, List, Optional
from data.ingestion.mock_feeder import MarketFeeder


class MarketReplayEngine:
    def __init__(self, feeder: MarketFeeder):
        self.feeder = feeder
        self.current_step = 0

    def run_replay(self, steps: int = 20, on_tick_callback: Optional[Callable[[int, Dict[str, Any]], None]] = None):
        """Advances market step-by-step and computes point-in-time updates."""
        for step in range(steps):
            self.current_step = step
            self.feeder.tick_market(drift_factor=0.03)

            snapshot = {
                "step": step,
                "tokens": self.feeder.scan_recent_tokens(limit=20),
                "prices": dict(self.feeder._price_state)
            }

            if on_tick_callback:
                on_tick_callback(step, snapshot)
