"""
Run Live Paper Trading Pipeline on Solana Markets.
"""

import os
import sys
import time

# Ensure project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config.settings import load_config
from app.core.logging_setup import setup_logger
from app.orchestration.orchestrator import MemeAlphaHunterOrchestrator
from dashboard.cli_dashboard import TerminalDashboard


def run_live_paper(cycles: int = 10, interval: float = 1.0):
    config = load_config()
    setup_logger("meme_alpha_hunter", log_level=config.log_level)
    orchestrator = MemeAlphaHunterOrchestrator(config)

    TerminalDashboard.render_header()
    print(f"🚀 Initializing Live Paper System with Initial Capital: ${config.portfolio.initial_capital_usd:.2f} USD")
    print(f"🔄 Executing {cycles} Market Tracking Cycles...\n")

    for i in range(1, cycles + 1):
        print(f"--- [Cycle {i:02d}/{cycles:02d}] ---")
        orchestrator.run_pipeline_cycle()

        # Simulate market dynamics progression
        if hasattr(orchestrator.provider, "tick_market"):
            orchestrator.provider.tick_market(drift_factor=0.02)

        time.sleep(interval)

    # Render Final Dashboard
    TerminalDashboard.render_header()
    summary = orchestrator.wallet.get_summary()
    TerminalDashboard.render_portfolio(summary, orchestrator.wallet.positions)
    TerminalDashboard.render_opportunities(orchestrator.top_opportunities)
    TerminalDashboard.render_health(orchestrator.health.get_system_summary())

    return orchestrator


if __name__ == "__main__":
    run_live_paper(cycles=8, interval=0.5)
