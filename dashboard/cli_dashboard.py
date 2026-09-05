"""
Rich Terminal Dashboard Renderer for Meme Alpha Hunter.
"""

from typing import Any, Dict, List
from app.core.database import DatabaseManager


class TerminalDashboard:
    @classmethod
    def render_header(cls):
        print("\n" + "=" * 80)
        print("  ⚡ MEME ALPHA HUNTER — SOLANA INTELLIGENCE & PAPER TRADING PLATFORM ⚡")
        print("=" * 80)

    @classmethod
    def render_portfolio(cls, summary: Dict[str, Any], positions: Dict[str, Any]):
        print("\n📊 [VIRTUAL WALLET STATUS]")
        print("-" * 80)
        print(f"  Starting Capital:  ${summary.get('initial_capital', 100.0):.2f} USD")
        print(f"  Current Equity:    ${summary.get('equity', 100.0):.2f} USD")
        print(f"  Available Cash:    ${summary.get('cash', 100.0):.2f} USD")
        print(f"  Open Positions:    ${summary.get('open_positions_val', 0.0):.2f} USD ({len(positions)} active)")
        print(f"  Realized PnL:      ${summary.get('realized_pnl', 0.0):+.2f} USD")
        print(f"  Unrealized PnL:    ${summary.get('unrealized_pnl', 0.0):+.2f} USD")
        print(f"  Total Fees:        -${summary.get('total_fees', 0.0):.2f} USD")
        print(f"  Total Slippage:    -${summary.get('total_slippage', 0.0):.2f} USD")
        print(f"  Max Drawdown:       {summary.get('max_drawdown_pct', 0.0):.1f}%")
        print("-" * 80)

        if positions:
            print("  [ACTIVE OPEN POSITIONS]")
            print("  {:<12} {:<12} {:<14} {:<14} {:<12} {:<15}".format("SYMBOL", "SIZE (USD)", "ENTRY PRICE", "CURR PRICE", "PnL ($)", "PnL (%)"))
            print("  " + "-" * 76)
            for pos in positions.values():
                print("  {:<12} ${:<11.2f} ${:<13.6f} ${:<13.6f} ${:<11.2f} {:<+14.2f}%".format(
                    pos.symbol, pos.size_usd, pos.entry_price, pos.current_price, pos.unrealized_pnl_usd, pos.unrealized_pnl_pct
                ))
            print("-" * 80)

    @classmethod
    def render_opportunities(cls, opps: List[Any]):
        print("\n🎯 [TOP OPPORTUNITY RANKINGS]")
        print("-" * 80)
        print("  {:<10} {:<8} {:<8} {:<8} {:<8} {:<8} {:<18} {:<12}".format(
            "SYMBOL", "ALPHA", "RISK", "CONF", "EARLY", "FINAL", "REGIME", "DECISION"
        ))
        print("  " + "-" * 76)
        for op in opps[:8]:
            if isinstance(op, dict):
                symbol = op.get("symbol", "N/A")
                alpha = float(op.get("alpha_score", 0))
                risk = float(op.get("risk_score", 0))
                conf = float(op.get("confidence_score", 0))
                early = float(op.get("earlyness_score", 0))
                final = float(op.get("final_score", 0))
                regime = str(op.get("regime", "N/A"))
                dec = str(op.get("recommendation", "N/A"))
            else:
                symbol = getattr(op, "symbol", "N/A")
                alpha = getattr(op, "alpha_score", 0.0)
                risk = getattr(op, "risk_score", 0.0)
                conf = getattr(op, "confidence_score", 0.0)
                early = getattr(op, "earlyness_score", 0.0)
                final = getattr(op, "final_score", 0.0)
                regime = getattr(op, "regime", "N/A")
                dec = getattr(op, "recommendation", "N/A")

            print("  {:<10} {:<8.1f} {:<8.1f} {:<8.1f} {:<8.1f} {:<8.1f} {:<18} {:<12}".format(
                symbol, alpha, risk, conf, early, final, str(regime), str(dec)
            ))
        print("-" * 80)

    @classmethod
    def render_health(cls, health_summary: Dict[str, Any]):
        print("\n🩺 [SYSTEM HEALTH]")
        print("-" * 80)
        print(f"  Overall System Status: [{health_summary.get('overall_status', 'HEALTHY')}]")
        for comp, data in health_summary.get("components", {}).items():
            print(f"  • {comp:<16}: [{data.get('status')}] - {data.get('message')}")
        print("=" * 80 + "\n")
