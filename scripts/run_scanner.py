"""
Run Solana Token Scanner.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config.settings import load_config
from app.core.logging_setup import setup_logger
from app.orchestration.orchestrator import MemeAlphaHunterOrchestrator
from dashboard.cli_dashboard import TerminalDashboard


def main():
    config = load_config()
    setup_logger("meme_alpha_hunter", log_level=config.log_level)
    orchestrator = MemeAlphaHunterOrchestrator(config)

    TerminalDashboard.render_header()
    orchestrator.run_pipeline_cycle()
    TerminalDashboard.render_opportunities(orchestrator.top_opportunities)
    TerminalDashboard.render_health(orchestrator.health.get_system_summary())


if __name__ == "__main__":
    main()
