"""
Configuration and settings module for Meme Alpha Hunter.
All parameters are strictly configurable and free of hardcoded magic numbers.
"""

from dataclasses import dataclass, field
import os
from typing import Dict, List, Optional


@dataclass
class NetworkConfig:
    chain: str = "solana"
    network: str = "mainnet-beta"
    rpc_endpoints: List[str] = field(default_factory=lambda: [
        "https://api.mainnet-beta.solana.com",
        "https://solana-mainnet.rpc.extrnode.com",
        "https://rpc.ankr.com/solana",
        "https://solana-api.projectserum.com"
    ])
    ws_endpoints: List[str] = field(default_factory=lambda: [
        "wss://api.mainnet-beta.solana.com"
    ])
    rpc_timeout_sec: float = 10.0
    max_retries: int = 3
    retry_backoff_base_sec: float = 0.5
    rate_limit_rps: float = 10.0


@dataclass
class DiscoveryConfig:
    min_liquidity_usd: float = 1_000.0
    min_volume_24h_usd: float = 500.0
    min_market_cap_usd: float = 2_000.0
    max_market_cap_usd: float = 100_000_000.0
    min_holders_count: int = 5
    max_token_age_hours: float = 720.0  # 30 days
    early_launch_age_limit_minutes: float = 120.0  # 2 hours
    discovery_poll_interval_sec: float = 1.0


@dataclass
class SecurityConfig:
    # Hard rejection criteria
    require_mint_authority_revoked: bool = True
    require_freeze_authority_revoked: bool = True
    max_single_holder_percent: float = 25.0
    max_top10_holders_percent: float = 65.0
    max_creator_allocation_percent: float = 15.0
    min_lp_locked_percent: float = 70.0
    max_rug_probability_for_sniper: float = 40.0
    min_security_score_for_entry: float = 60.0
    hard_reject_honeypot: bool = True
    hard_reject_freeze_enabled: bool = True
    hard_reject_extreme_concentration: bool = True


@dataclass
class ScoringConfig:
    # Weights for Alpha Score calculation (sum = 1.0)
    weight_microstructure: float = 0.25
    weight_smart_money: float = 0.25
    weight_whale_radar: float = 0.15
    weight_momentum_acceleration: float = 0.20
    weight_narrative_heat: float = 0.15

    # Thresholds for opportunity classification
    min_alpha_score: float = 65.0
    max_risk_score: float = 45.0
    min_confidence_score: float = 55.0
    min_opportunity_score: float = 70.0


@dataclass
class ExecutionConfig:
    # Execution simulation & fees
    simulated_dex_fee_percent: float = 0.25  # 0.25% Raydium/Orca standard fee
    simulated_solana_base_fee_usd: float = 0.005  # Standard signature fee (~0.000005 SOL)
    simulated_priority_fee_usd: float = 0.010  # Micro-lamport priority fee (~0.00005 SOL)
    base_slippage_percent: float = 0.50  # 0.5% base slippage
    liquidity_impact_constant: float = 0.15  # Quadratic impact factor size / liquidity
    default_latency_ms: int = 500  # Default simulated execution latency
    partial_fill_threshold_usd: float = 500.0  # Fills partially if size is large vs depth
    enable_partial_fills: bool = True


@dataclass
class PortfolioConfig:
    initial_capital_usd: float = 100.0
    currency: str = "USD"
    max_open_positions: int = 5
    max_position_size_usd: float = 25.0  # Max 25% of starting capital in one token
    min_position_size_usd: float = 5.0
    max_portfolio_heat_percent: float = 80.0  # Max 80% total capital allocated
    max_daily_loss_percent: float = 15.0  # Circuit breaker: pause if daily loss > 15%
    max_drawdown_limit_percent: float = 25.0  # Emergency breaker
    consecutive_loss_breaker_count: int = 4  # Pause if 4 consecutive losses


@dataclass
class ExitConfig:
    take_profit_target_1_percent: float = 15.0  # First TP target (+15%)
    take_profit_target_1_sell_ratio: float = 1.0  # Close full position on target
    take_profit_target_2_percent: float = 35.0  # Second TP target (+35%)
    take_profit_target_2_sell_ratio: float = 1.0  # Sell 100%
    take_profit_target_3_percent: float = 75.0  # Final TP target (+75%)
    stop_loss_percent: float = 10.0  # Hard stop loss (-10%)
    trailing_stop_activation_percent: float = 12.0  # Activate trailing after +12% gain
    trailing_stop_distance_percent: float = 5.0  # Trail 5% below peak price
    max_holding_time_minutes: float = 120.0  # Time-based decay exit (2 hours)
    exit_on_smart_money_dump: bool = True
    exit_on_liquidity_drain: bool = True


@dataclass
class StrategyConfig:
    name: str = "Balanced"
    min_alpha: float = 65.0
    max_risk: float = 45.0
    min_confidence: float = 60.0
    position_size_percent: float = 15.0
    stop_loss_percent: float = 15.0
    take_profit_percent: float = 50.0
    use_trailing_stop: bool = True


@dataclass
class TelegramConfig:
    enabled: bool = False
    bot_token: Optional[str] = None
    chat_id: Optional[str] = None
    alert_on_alpha_score: float = 80.0
    alert_on_whale_buy_usd: float = 5_000.0
    alert_on_rug_warning: bool = True


@dataclass
class AppConfig:
    network: NetworkConfig = field(default_factory=NetworkConfig)
    discovery: DiscoveryConfig = field(default_factory=DiscoveryConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    scoring: ScoringConfig = field(default_factory=ScoringConfig)
    execution: ExecutionConfig = field(default_factory=ExecutionConfig)
    portfolio: PortfolioConfig = field(default_factory=PortfolioConfig)
    exit_rules: ExitConfig = field(default_factory=ExitConfig)
    telegram: TelegramConfig = field(default_factory=TelegramConfig)
    data_mode: str = "live"  # "live", "mock", "replay"
    strict_provenance: bool = True
    fail_on_mock_contamination: bool = True
    db_path: str = "data/meme_hunter.db"
    log_level: str = "INFO"
    environment: str = "paper_trading"


def load_config() -> AppConfig:
    """Load configuration with optional environment variable overrides."""
    config = AppConfig()

    # Environment variable overrides
    if os.getenv("DATA_MODE"):
        config.data_mode = os.getenv("DATA_MODE").lower()
    if os.getenv("SOLANA_RPC_URL"):
        config.network.rpc_endpoints = [os.getenv("SOLANA_RPC_URL")] + config.network.rpc_endpoints
    if os.getenv("INITIAL_CAPITAL"):
        config.portfolio.initial_capital_usd = float(os.getenv("INITIAL_CAPITAL"))
    if os.getenv("DB_PATH"):
        config.db_path = os.getenv("DB_PATH")
    if os.getenv("LOG_LEVEL"):
        config.log_level = os.getenv("LOG_LEVEL").upper()
    if os.getenv("TELEGRAM_BOT_TOKEN") and os.getenv("TELEGRAM_CHAT_ID"):
        config.telegram.enabled = True
        config.telegram.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        config.telegram.chat_id = os.getenv("TELEGRAM_CHAT_ID")

    return config
