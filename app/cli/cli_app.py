"""
Command Line Interface for Meme Alpha Hunter.
"""

import argparse
import sys
import time

from app.config.settings import load_config
from app.core.logging_setup import setup_logger
from app.orchestration.orchestrator import MemeAlphaHunterOrchestrator
from dashboard.cli_dashboard import TerminalDashboard


def main():
    parser = argparse.ArgumentParser(description="Meme Alpha Hunter — Solana Intelligence & Paper Trading")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Command: scan
    subparsers.add_parser("scan", help="Scan Solana token market for new and active meme coins")

    # Command: live-paper
    paper_parser = subparsers.add_parser("live-paper", help="Run live paper trading engine")
    paper_parser.add_argument("--cycles", type=int, default=5, help="Number of pipeline cycles to execute")
    paper_parser.add_argument("--interval", type=float, default=2.0, help="Interval between cycles in seconds")

    # Command: whales
    subparsers.add_parser("whales", help="Display recent whale activity and radar netflows")

    # Command: portfolio
    subparsers.add_parser("portfolio", help="Show virtual wallet equity, open positions, and PnL")

    # Command: trades
    subparsers.add_parser("trades", help="Display trade journal history")

    # Command: backtest
    subparsers.add_parser("backtest", help="Run multi-strategy backtest and benchmark comparison")

    # Command: health
    subparsers.add_parser("health", help="Check system components health status")

    args = parser.parse_args()
    config = load_config()
    setup_logger("meme_alpha_hunter", log_level=config.log_level)

    orchestrator = MemeAlphaHunterOrchestrator(config)

    if args.command == "scan":
        TerminalDashboard.render_header()
        res = orchestrator.run_pipeline_cycle()
        TerminalDashboard.render_opportunities(orchestrator.top_opportunities)
        TerminalDashboard.render_health(orchestrator.health.get_system_summary())

    elif args.command == "live-paper":
        TerminalDashboard.render_header()
        print(f"Starting Live Paper Trading Engine for {args.cycles} cycles...\n")
        for c in range(1, args.cycles + 1):
            print(f"\n>>> Running Cycle {c}/{args.cycles} <<<")
            orchestrator.run_pipeline_cycle()
            # Advance simulated price movements
            if hasattr(orchestrator.provider, "tick_market"):
                orchestrator.provider.tick_market()
            time.sleep(args.interval)

        summary = orchestrator.wallet.get_summary()
        TerminalDashboard.render_portfolio(summary, orchestrator.wallet.positions)
        TerminalDashboard.render_opportunities(orchestrator.top_opportunities)
        TerminalDashboard.render_health(orchestrator.health.get_system_summary())

    elif args.command == "portfolio":
        TerminalDashboard.render_header()
        summary = orchestrator.wallet.get_summary()
        TerminalDashboard.render_portfolio(summary, orchestrator.wallet.positions)

    elif args.command == "health":
        TerminalDashboard.render_header()
        TerminalDashboard.render_health(orchestrator.health.get_system_summary())

    else:
        # Default behavior: run 1 cycle and print dashboard
        TerminalDashboard.render_header()
        orchestrator.run_pipeline_cycle()
        TerminalDashboard.render_portfolio(orchestrator.wallet.get_summary(), orchestrator.wallet.positions)
        TerminalDashboard.render_opportunities(orchestrator.top_opportunities)
        TerminalDashboard.render_health(orchestrator.health.get_system_summary())


if __name__ == "__main__":
    main()
