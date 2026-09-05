"""
Event Bus for asynchronous and decoupled event-driven processing.
Supports publish/subscribe patterns with topic isolation and error handling.
"""

from collections import defaultdict
import logging
from typing import Any, Callable, Dict, List

logger = logging.getLogger("meme_alpha_hunter.event_bus")


class EventBus:
    def __init__(self):
        self._subscribers: Dict[str, List[Callable[[Dict[str, Any]], None]]] = defaultdict(list)

    def subscribe(self, topic: str, handler: Callable[[Dict[str, Any]], None]):
        """Subscribe a callback to a topic."""
        self._subscribers[topic].append(handler)

    def publish(self, topic: str, event_data: Dict[str, Any]):
        """Publish an event to all subscribers of a topic."""
        handlers = self._subscribers.get(topic, [])
        for handler in handlers:
            try:
                handler(event_data)
            except Exception as e:
                logger.error(f"Error in handler {handler.__name__} for topic {topic}: {e}", exc_info=True)


# Global singleton instance
bus = EventBus()
