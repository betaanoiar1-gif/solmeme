"""
Command Line Interface for Meme Alpha Hunter.
Supports Real Live Solana Execution, On-Chain Verification, Paper Trading,
Intelligence Dashboards, and Multi-Strategy Backtesting.
"""

import argparse
import sys
import time

from app.config.settings import load_config
from app.core.logging_setup import setup_logger
from app.orchestration.live_paper_engine import RealLivePaperEngine
from app.orchestration.orchestrator import MemeAlphaHunterOrchestrator
from dashboard.cli_dashboard import TerminalDashboard


def main():
    parser = argparse.ArgumentParser(description="Meme Alpha Hunter — Solana Intelligence & Paper Trading")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Command: scan
    scan_parser = subparsers.add_parser("scan", help="Scan Solana token market for new and active meme coins")
    scan_parser.add_argument("--mode", choices=["live", "mock"], default="live", help="Data source mode")

    # Command: live-paper
    paper_parser = subparsers.add_parser("live-paper", help="Run real live paper trading engine")
    paper_parser.add_argument("--mode", choices=["live", "mock", "real-onchain"], default="live", help="Execution mode")
    paper_parser.add_argument("--cycles", type=int, default=5, help="Number of pipeline cycles to execute")
    paper_parser.add_argument("--interval", type=float, default=1.0, help="Interval between cycles in seconds")

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

    if args.command == "live-paper":
        TerminalDashboard.render_header()
        print(f"🚀 [REAL LIVE PAPER ENGINE] Initializing mode: {args.mode.upper()} ({args.cycles} cycles)...\n")

        live_engine = RealLivePaperEngine(config)

        for c in range(1, args.cycles + 1):
            res = live_engine.run_live_cycle()
            print(f"[{c:02d}/{args.cycles:02d}] Discovered: {res.real_tokens_discovered} | Verified Mints: {res.real_tokens_verified} | Real Swaps: {res.real_swaps_ingested} | Real Whales: {res.real_whale_events} | Equity: ${res.ending_equity_usd:.2f} | Invariants: {res.accounting_status}")
            time.sleep(args.interval)

        summary = live_engine.wallet.get_summary()
        TerminalDashboard.render_portfolio(summary, live_engine.wallet.positions)
        TerminalDashboard.render_opportunities(live_engine.top_opportunities)
        TerminalDashboard.render_health(live_engine.health.get_system_summary())

    elif args.command == "scan":
        orchestrator = MemeAlphaHunterOrchestrator(config)
        TerminalDashboard.render_header()
        res = orchestrator.run_pipeline_cycle()
        TerminalDashboard.render_opportunities(orchestrator.top_opportunities)
        TerminalDashboard.render_health(orchestrator.health.get_system_summary())

    elif args.command == "portfolio":
        orchestrator = MemeAlphaHunterOrchestrator(config)
        TerminalDashboard.render_header()
        summary = orchestrator.wallet.get_summary()
        TerminalDashboard.render_portfolio(summary, orchestrator.wallet.positions)

    elif args.command == "health":
        orchestrator = MemeAlphaHunterOrchestrator(config)
        TerminalDashboard.render_header()
        TerminalDashboard.render_health(orchestrator.health.get_system_summary())

    else:
        # Default behavior: run 1 cycle and print dashboard
        orchestrator = MemeAlphaHunterOrchestrator(config)
        TerminalDashboard.render_header()
        orchestrator.run_pipeline_cycle()
        TerminalDashboard.render_portfolio(orchestrator.wallet.get_summary(), orchestrator.wallet.positions)
        TerminalDashboard.render_opportunities(orchestrator.top_opportunities)
        TerminalDashboard.render_health(orchestrator.health.get_system_summary())


if __name__ == "__main__":
    main()
