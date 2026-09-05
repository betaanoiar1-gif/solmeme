"""
Multi-Strategy Virtual Portfolio Suite.
Simulates 5 distinct virtual portfolios (A, B, C, D, E) starting with $100 each.
"""

from typing import Dict, List, Optional
from app.config.settings import StrategyConfig
from portfolio.virtual_wallet.virtual_wallet import VirtualWallet


class MultiStrategySuite:
    def __init__(self, initial_capital_each: float = 100.0):
        self.strategies: Dict[str, StrategyConfig] = {
            "Portfolio A (Conservative)": StrategyConfig(
                name="Portfolio A (Conservative)",
                min_alpha=75.0,
                max_risk=30.0,
                min_confidence=70.0,
                position_size_percent=10.0,
                stop_loss_percent=10.0,
                take_profit_percent=40.0
            ),
            "Portfolio B (Balanced)": StrategyConfig(
                name="Portfolio B (Balanced)",
                min_alpha=65.0,
                max_risk=45.0,
                min_confidence=60.0,
                position_size_percent=15.0,
                stop_loss_percent=15.0,
                take_profit_percent=50.0
            ),
            "Portfolio C (Aggressive)": StrategyConfig(
                name="Portfolio C (Aggressive)",
                min_alpha=55.0,
                max_risk=60.0,
                min_confidence=50.0,
                position_size_percent=25.0,
                stop_loss_percent=20.0,
                take_profit_percent=75.0
            ),
            "Portfolio D (Smart Money)": StrategyConfig(
                name="Portfolio D (Smart Money)",
                min_alpha=68.0,
                max_risk=40.0,
                min_confidence=65.0,
                position_size_percent=18.0,
                stop_loss_percent=12.0,
                take_profit_percent=60.0
            ),
            "Portfolio E (Hybrid AI)": StrategyConfig(
                name="Portfolio E (Hybrid AI)",
                min_alpha=70.0,
                max_risk=38.0,
                min_confidence=65.0,
                position_size_percent=20.0,
                stop_loss_percent=14.0,
                take_profit_percent=65.0
            )
        }

        self.wallets: Dict[str, VirtualWallet] = {
            name: VirtualWallet(name=name, initial_capital_usd=initial_capital_each)
            for name in self.strategies.keys()
        }

    def update_all_prices(self, price_map: Dict[str, float]):
        for wallet in self.wallets.values():
            wallet.update_prices(price_map)

    def get_all_summaries(self) -> List[Dict[str, any]]:
        return [wallet.get_summary() for wallet in self.wallets.values()]
