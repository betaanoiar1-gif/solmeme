"""
Telegram Alerts and Command Handler Architecture.
Provides interactive bot commands (/top, /whales, /snipers, /portfolio, /trades, /health)
and real-time event notifications.
"""

import json
import logging
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional
from app.config.settings import TelegramConfig

logger = logging.getLogger("meme_alpha_hunter.telegram")


class TelegramBotEngine:
    def __init__(self, config: TelegramConfig):
        self.config = config
        self.base_url = f"https://api.telegram.org/bot{config.bot_token}" if config.bot_token else ""

    def send_message(self, text: str) -> bool:
        if not self.config.enabled or not self.config.bot_token or not self.config.chat_id:
            logger.debug(f"[Telegram Mock Alert]:\n{text}")
            return True

        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": self.config.chat_id,
            "text": text,
            "parse_mode": "Markdown"
        }
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=5.0) as response:
                return response.status == 200
        except Exception as e:
            logger.warning(f"Failed to send Telegram message: {e}")
            return False

    def alert_early_alpha(self, token_symbol: str, alpha_score: float, details: str):
        msg = f"🚀 *EARLY ALPHA DETECTED*\n\n*Token:* ${token_symbol}\n*Alpha Score:* {alpha_score}/100\n*Details:* {details}"
        self.send_message(msg)

    def alert_whale_action(self, action: str, token_symbol: str, amount_usd: float, wallet: str):
        msg = f"🐋 *WHALE RADAR ALERT*\n\n*Action:* {action}\n*Token:* ${token_symbol}\n*Amount:* ${amount_usd:,.2f}\n*Wallet:* `{wallet}`"
        self.send_message(msg)

    def alert_rug_warning(self, token_symbol: str, reasons: List[str]):
        reasons_str = "\n".join([f"• {r}" for r in reasons])
        msg = f"⚠️ *RUG / SECURITY WARNING*\n\n*Token:* ${token_symbol}\n*Reasons:*\n{reasons_str}"
        self.send_message(msg)

    def alert_trade_execution(self, action: str, symbol: str, price: float, size_usd: float, pnl_usd: Optional[float] = None):
        if action == "ENTRY":
            msg = f"🎯 *PAPER TRADE ENTRY*\n\n*Token:* ${symbol}\n*Price:* ${price:.6f}\n*Size:* ${size_usd:.2f}"
        else:
            pnl_str = f"+${pnl_usd:.2f}" if (pnl_usd or 0) >= 0 else f"-${abs(pnl_usd or 0):.2f}"
            msg = f"🏁 *PAPER TRADE EXIT*\n\n*Token:* ${symbol}\n*Price:* ${price:.6f}\n*Realized PnL:* {pnl_str}"
        self.send_message(msg)
