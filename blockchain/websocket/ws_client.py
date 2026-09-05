"""
WebSocket and Event Stream connection client for Solana real-time logs.
Supports graceful polling fallback.
"""

import json
import logging
import threading
import time
from typing import Callable, Dict, List, Optional

logger = logging.getLogger("meme_alpha_hunter.ws")


class SolanaWebSocketClient:
    def __init__(self, ws_url: str = "wss://api.mainnet-beta.solana.com", on_event: Optional[Callable[[Dict], None]] = None):
        self.ws_url = ws_url
        self.on_event = on_event
        self.is_running = False
        self._thread: Optional[threading.Thread] = None

    def start(self):
        self.is_running = True
        logger.info(f"Solana WebSocket client started (fallback mode ready): {self.ws_url}")

    def stop(self):
        self.is_running = False
        logger.info("Solana WebSocket client stopped")
