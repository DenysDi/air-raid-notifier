"""
Client for the alerts.in.ua API.
Docs: https://devs.alerts.in.ua/
"""

import logging
import requests

logger = logging.getLogger(__name__)

ALERT_STATUS_ACTIVE = "A"
ALERT_STATUS_PARTIAL = "P"
ALERT_STATUS_NONE = "N"

ACTIVE_STATUSES = {ALERT_STATUS_ACTIVE, ALERT_STATUS_PARTIAL}


class AlertsClient:
    BASE_URL = "https://api.alerts.in.ua"

    def __init__(self, config: dict):
        self.token = config["token"]
        self.region_uid = str(config["region_uid"])
        self.alert_on_partial = config.get("alert_on_partial", True)
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})

    def check_alert(self) -> bool:
        """
        Returns True if there is an active (or partial, if configured) air
        raid alert in the configured region.
        Raises requests.RequestException on network/API errors.
        """
        url = f"{self.BASE_URL}/v1/iot/active_air_raid_alerts/{self.region_uid}.json"
        resp = self.session.get(url, timeout=10)
        resp.raise_for_status()

        data = resp.json()
        # Response: {"status": "A"} | {"status": "P"} | {"status": "N"}
        status = data.get("status", ALERT_STATUS_NONE)

        if status == ALERT_STATUS_ACTIVE:
            return True
        if status == ALERT_STATUS_PARTIAL and self.alert_on_partial:
            return True
        return False
