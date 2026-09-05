"""
Tests for Virtual Wallet, Position Sizing, Risk Manager, and Multi-Strategy.
"""

import unittest
from app.config.settings import PortfolioConfig
from portfolio.accounting.multi_strategy import MultiStrategySuite
from portfolio.position_manager.position_manager import PositionManager
from portfolio.risk_manager.risk_manager import PortfolioRiskManager
from portfolio.virtual_wallet.virtual_wallet import VirtualWallet
from simulation.execution.execution_engine import ExecutionSimulator


class TestPortfolio(unittest.TestCase):
    def setUp(self):
        self.config = PortfolioConfig(initial_capital_usd=100.0, max_position_size_usd=25.0)
        self.wallet = VirtualWallet(initial_capital_usd=100.0)
        self.exec_sim = ExecutionSimulator()

    def test_virtual_wallet_lifecycle(self):
        self.assertEqual(self.wallet.cash_usd, 100.0)
        self.assertEqual(self.wallet.equity_usd, 100.0)

        # Open position
        exec_res = self.exec_sim.execute_order(market_price=0.10, trade_size_usd=20.0, liquidity_usd=50_000.0, is_buy=True)
        pos = self.wallet.open_position("MintABC", "ABC", exec_res)
        self.assertIsNotNone(pos)
        self.assertLess(self.wallet.cash_usd, 80.0)

        # Mark-to-market price up (+50%)
        self.wallet.update_prices({"MintABC": 0.15})
        self.assertGreater(self.wallet.equity_usd, 105.0)

        # Close position
        exec_sell = self.exec_sim.execute_order(market_price=0.15, trade_size_usd=pos.current_value_usd, liquidity_usd=50_000.0, is_buy=False)
        closed_pos = self.wallet.close_position("MintABC", exec_sell)
        self.assertIsNotNone(closed_pos)
        self.assertGreater(self.wallet.realized_pnl_usd, 0.0)
        self.assertEqual(len(self.wallet.positions), 0)

    def test_circuit_breakers(self):
        risk_mgr = PortfolioRiskManager(self.config)

        # 4 consecutive losses trigger circuit breaker
        for _ in range(4):
            risk_mgr.register_trade_outcome(is_win=False)

        check = risk_mgr.evaluate_risk(current_equity=80.0, current_cash=80.0, max_drawdown_pct=20.0)
        self.assertFalse(check.allowed_to_trade)
        self.assertTrue(check.is_circuit_breaker_active)

    def test_multi_strategy_suite(self):
        suite = MultiStrategySuite(initial_capital_each=100.0)
        self.assertEqual(len(suite.wallets), 5)
        summaries = suite.get_all_summaries()
        for s in summaries:
            self.assertEqual(s["initial_capital"], 100.0)


if __name__ == "__main__":
    unittest.main()
