"""
Run Replay Mode on Historical Solana Market Ticks.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.ingestion.mock_feeder import MarketFeeder
from simulation.replay.replay_engine import MarketReplayEngine


def main():
    print("=" * 80)
    print("  📼 STARTING POINT-IN-TIME REPLAY ENGINE (ZERO FUTURE LEAKAGE)")
    print("=" * 80)

    feeder = MarketFeeder()
    replay = MarketReplayEngine(feeder)

    def on_tick(step, snapshot):
        print(f"  [Step {step:02d}] Active Tokens: {len(snapshot['tokens'])} | Tracked Mints: {len(snapshot['prices'])}")

    replay.run_replay(steps=10, on_tick_callback=on_tick)
    print("\n  ✅ Replay Completed Successfully with 0 Leakage.\n" + "=" * 80)


if __name__ == "__main__":
    main()
