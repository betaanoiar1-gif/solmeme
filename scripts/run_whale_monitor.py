"""
Run Whale Radar & Smart Money Monitor.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config.settings import load_config
from app.core.database import DatabaseManager
from app.core.logging_setup import setup_logger
from app.orchestration.orchestrator import MemeAlphaHunterOrchestrator


def main():
    config = load_config()
    setup_logger("meme_alpha_hunter", log_level=config.log_level)
    orchestrator = MemeAlphaHunterOrchestrator(config)
    orchestrator.run_pipeline_cycle()

    db = DatabaseManager(config.db_path)
    events = db.get_whale_events(limit=20)

    print("\n🐋 [WHALE RADAR DETECTIONS]")
    print("=" * 80)
    print("  {:<10} {:<20} {:<15} {:<15} {:<12}".format("ACTION", "WALLET", "MINT", "AMOUNT (USD)", "IMPACT"))
    print("  " + "-" * 76)
    for ev in events:
        print("  {:<10} {:<20} {:<15} ${:<14,.2f} {:<12.1f}%".format(
            ev["action"], ev["wallet"][:18] + "..", ev["mint"][:12] + "..", ev["amount_usd"], ev["impact_score"]
        ))
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
