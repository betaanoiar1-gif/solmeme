"""
Opportunity Discovery Queue.
Prioritizes newly discovered tokens for intelligence and security evaluation.
"""

from collections import deque
import threading
from typing import List, Optional
from discovery.token_discovery.token_scanner import DiscoveredToken


class OpportunityQueue:
    def __init__(self, maxsize: int = 500):
        self._queue = deque(maxlen=maxsize)
        self._seen_mints = set()
        self._lock = threading.Lock()

    def push(self, token: DiscoveredToken):
        with self._lock:
            if token.mint not in self._seen_mints:
                self._seen_mints.add(token.mint)
                self._queue.append(token)

    def pop(self) -> Optional[DiscoveredToken]:
        with self._lock:
            if self._queue:
                return self._queue.popleft()
            return None

    def size(self) -> int:
        with self._lock:
            return len(self._queue)

    def clear(self):
        with self._lock:
            self._queue.clear()
            self._seen_mints.clear()
