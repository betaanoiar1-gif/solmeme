"""
Run Dedicated Solana Sniper Modes (Modes A-E).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config.settings import load_config
from app.core.logging_setup import setup_logger
from app.orchestration.orchestrator import MemeAlphaHunterOrchestrator


def main():
    config = load_config()
    setup_logger("meme_alpha_hunter", log_level=config.log_level)
    orchestrator = MemeAlphaHunterOrchestrator(config)

    print("=" * 80)
    print("  🎯 RUNNING SOLANA SNIPER EVALUATION ENGINE (MODES A, B, C, D, E)")
    print("=" * 80)

    orchestrator.run_pipeline_cycle()

    print("\n[ACTIVE SNIPER STAGES]")
    print("-" * 80)
    print("  {:<12} {:<15} {:<15} {:<15}".format("SYMBOL", "STAGE", "ALPHA", "RISK"))
    print("  " + "-" * 76)
    for opp in orchestrator.top_opportunities:
        stage = orchestrator.state_machine.get_state(opp.mint)
        print("  {:<12} {:<15} {:<15.1f} {:<15.1f}".format(
            opp.symbol, stage.value, opp.alpha_score, opp.risk_score
        ))
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
