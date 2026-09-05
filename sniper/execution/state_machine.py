"""
Sniper State Machine.
Manages sniper stages from S0_WATCH to S7_EXIT and SX_KILL.
"""

from enum import Enum
from typing import Dict, Optional


class SniperStage(str, Enum):
    S0_WATCH = "S0_WATCH"
    S1_EARLY_DETECTION = "S1_EARLY_DETECTION"
    S2_QUALIFIED = "S2_QUALIFIED"
    S3_SNIPER_READY = "S3_SNIPER_READY"
    S4_PAPER_EXECUTION = "S4_PAPER_EXECUTION"
    S5_HOLD = "S5_HOLD"
    S6_REDUCE = "S6_REDUCE"
    S7_EXIT = "S7_EXIT"
    SX_KILL = "SX_KILL"


class SniperStateMachine:
    def __init__(self):
        self._states: Dict[str, SniperStage] = {}

    def get_state(self, mint: str) -> SniperStage:
        return self._states.get(mint, SniperStage.S0_WATCH)

    def transition(self, mint: str, new_state: SniperStage) -> SniperStage:
        curr = self.get_state(mint)
        self._states[mint] = new_state
        return new_state
