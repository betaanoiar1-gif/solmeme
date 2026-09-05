"""
System Health Monitoring for Meme Alpha Hunter.
Tracks subsystem health: HEALTHY, DEGRADED, FAILED.
"""

from datetime import datetime
from enum import Enum
import time
from typing import Dict, Optional

from app.core.database import DatabaseManager


class HealthStatus(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    FAILED = "FAILED"


class HealthMonitor:
    def __init__(self, db: Optional[DatabaseManager] = None):
        self.db = db or DatabaseManager()
        self._statuses: Dict[str, Dict[str, any]] = {
            "RPC": {"status": HealthStatus.HEALTHY, "message": "Initialized"},
            "WEBSOCKET": {"status": HealthStatus.HEALTHY, "message": "Initialized"},
            "DISCOVERY": {"status": HealthStatus.HEALTHY, "message": "Initialized"},
            "SECURITY": {"status": HealthStatus.HEALTHY, "message": "Initialized"},
            "SCORING": {"status": HealthStatus.HEALTHY, "message": "Initialized"},
            "PAPER_TRADING": {"status": HealthStatus.HEALTHY, "message": "Initialized"},
            "DATABASE": {"status": HealthStatus.HEALTHY, "message": "Connected"}
        }

    def record_status(self, component: str, status: HealthStatus, message: str = ""):
        self._statuses[component] = {
            "status": status,
            "message": message,
            "updated_at": time.time()
        }
        try:
            self.db.update_health(component, status.value, message, time.time())
        except Exception:
            pass

    def get_component_status(self, component: str) -> Dict[str, any]:
        return self._statuses.get(component, {"status": HealthStatus.FAILED, "message": "Unknown component"})

    def get_system_summary(self) -> Dict[str, any]:
        overall = HealthStatus.HEALTHY
        for comp, data in self._statuses.items():
            if data["status"] == HealthStatus.FAILED:
                overall = HealthStatus.FAILED
                break
            elif data["status"] == HealthStatus.DEGRADED and overall != HealthStatus.FAILED:
                overall = HealthStatus.DEGRADED

        return {
            "overall_status": overall.value,
            "components": {k: {"status": v["status"].value if isinstance(v["status"], HealthStatus) else v["status"], "message": v["message"]} for k, v in self._statuses.items()},
            "timestamp": datetime.utcnow().isoformat()
        }
