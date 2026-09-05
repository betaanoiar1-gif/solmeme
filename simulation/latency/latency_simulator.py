"""
Latency Simulator for Solana execution delays (250ms to 10,000ms).
"""

from dataclasses import dataclass
import random
import time


@dataclass
class LatencyProfile:
    detection_ts: float
    decision_ts: float
    execution_ts: float
    latency_ms: int
    slippage_drift_factor: float


class LatencySimulator:
    LATENCY_MODES = {
        "ultra_fast": 250,
        "fast": 500,
        "standard": 1000,
        "congested": 3000,
        "high_congestion": 5000,
        "extreme": 10000
    }

    @classmethod
    def simulate(cls, mode: str = "fast", base_ms: int = 500) -> LatencyProfile:
        target_ms = cls.LATENCY_MODES.get(mode, base_ms)
        actual_ms = int(random.gauss(target_ms, target_ms * 0.15))
        actual_ms = max(actual_ms, 50)

        now = time.time()
        decision_ts = now + (actual_ms * 0.3) / 1000.0
        exec_ts = now + (actual_ms) / 1000.0

        # Small drift during the latency window
        drift = random.gauss(0.0002, 0.001) * (actual_ms / 1000.0)

        return LatencyProfile(
            detection_ts=now,
            decision_ts=decision_ts,
            execution_ts=exec_ts,
            latency_ms=actual_ms,
            slippage_drift_factor=drift
        )
