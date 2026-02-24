"""
Microsoft Teams messenger integration via Microsoft Graph API.

What this integration does:
  - Sets the user's Teams *presence* (Available → DoNotDisturb) and
    *status message* during an air-raid alert, then restores both.

Required setup:
  1. Sign in to https://portal.azure.com → Azure Active Directory → App registrations
     → New registration.
       Name: "Air Raid Notifier"
       Supported account types: "Accounts in this organizational directory only"
       Redirect URI: leave empty for now.

  2. After creation note the "Application (client) ID" and "Directory (tenant) ID".

  3. Go to "Certificates & secrets" → New client secret → copy the VALUE immediately.

  4. Go to "API permissions" → Add a permission → Microsoft Graph →
     Application permissions → add:
         Presence.ReadWrite.All

  5. Click "Grant admin consent for <tenant>".

  6. Get your Teams user Object ID:
       Open https://portal.azure.com → Azure Active Directory → Users
       → find yourself → copy "Object ID".

  7. Fill in config.yaml:
       messengers:
         teams:
           enabled: true
           tenant_id:     "<Directory (tenant) ID>"
           client_id:     "<Application (client) ID>"
           client_secret: "<secret value>"
           user_id:       "<your Object ID>"
           alert_presence:  "DoNotDisturb"   # Available | Busy | DoNotDisturb | Away
           alert_text:    "Air Raid 🚀"

Notes:
  - Presence.ReadWrite.All is an *application* permission – no user sign-in needed.
  - The presence override lasts for `presence_ttl_seconds` (default 3600).
    The main loop refreshes it before it expires.
  - Status messages use the /setStatusMessage endpoint (delegated only in Graph).
    Because we use app-only auth, only the presence is set – not the chat status
    message.  If you want the status message too, see the README for an alternative
    setup using delegated (interactive) auth.
"""

import logging
import time
from typing import Optional

import requests

from .base import BaseMessenger, Status

logger = logging.getLogger(__name__)

GRAPH_BASE = "https://graph.microsoft.com/v1.0"
TOKEN_URL_TEMPLATE = "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"

# Teams presence values accepted by the API
VALID_PRESENCES = {
    "Available", "Busy", "DoNotDisturb", "BeRightBack", "Away", "Offline"
}


class TeamsMessenger(BaseMessenger):
    name = "Teams"

    def __init__(self, config: dict):
        super().__init__(config)
        for key in ("tenant_id", "client_id", "client_secret", "user_id"):
            if not config.get(key):
                raise ValueError(f"teams.{key} is required")

        self.tenant_id = config["tenant_id"]
        self.client_id = config["client_id"]
        self.client_secret = config["client_secret"]
        self.user_id = config["user_id"]

        self.alert_presence = config.get("alert_presence", "DoNotDisturb")
        if self.alert_presence not in VALID_PRESENCES:
            raise ValueError(
                f"teams.alert_presence must be one of {sorted(VALID_PRESENCES)}"
            )

        # TTL for a single presence override call (seconds).  Max allowed is 3600.
        self.presence_ttl = min(int(config.get("presence_ttl_seconds", 3600)), 3600)

        self._access_token: Optional[str] = None
        self._token_expiry: float = 0.0
        self.session = requests.Session()

    # ------------------------------------------------------------------
    # BaseMessenger interface
    # ------------------------------------------------------------------

    def get_status(self) -> Status:
        """Fetch current presence from Graph API."""
        token = self._get_token()
        url = f"{GRAPH_BASE}/users/{self.user_id}/presence"
        resp = self.session.get(
            url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        # availability: "Available" | "Busy" | "DoNotDisturb" | "Away" | …
        # activity:     "Available" | "InAMeeting" | "InACall" | …
        availability = data.get("availability", "Available")
        activity = data.get("activity", "")
        return Status(
            text=availability,
            emoji="",
            extra={"activity": activity},
        )

    def set_status(self, status: Status) -> None:
        """
        Set presence override via Graph API.
        status.text must be a valid Teams presence value.
        """
        presence_value = status.extra.get("presence_override", status.text)
        if presence_value not in VALID_PRESENCES:
            # Fall back to Available for restore, DoNotDisturb for alert
            presence_value = "Available"

        token = self._get_token()
        url = f"{GRAPH_BASE}/users/{self.user_id}/presence/setPresence"
        payload = {
            "sessionId": self.client_id,   # stable identifier for our app session
            "availability": presence_value,
            "activity": presence_value,
            "expirationDuration": f"PT{self.presence_ttl}S",
        }
        resp = self.session.post(
            url,
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        resp.raise_for_status()

    # ------------------------------------------------------------------
    # Override helpers to pass the correct presence value
    # ------------------------------------------------------------------

    def set_alert(self) -> None:
        """Activate air-raid presence."""
        alert_status = Status(
            text=self.alert_presence,
            emoji="",
            extra={"presence_override": self.alert_presence},
        )
        try:
            self.set_status(alert_status)
            logger.info("[%s] Alert presence set to %s.", self.name, self.alert_presence)
        except Exception as exc:
            logger.error("[%s] Could not set alert presence: %s", self.name, exc)

    def restore_status(self) -> None:
        """Restore previous presence."""
        if self._saved_status is None:
            logger.warning("[%s] No saved status to restore.", self.name)
            return
        saved_availability = self._saved_status.text
        restore_status = Status(
            text=saved_availability,
            emoji="",
            extra={"presence_override": saved_availability},
        )
        try:
            self.set_status(restore_status)
            logger.info("[%s] Presence restored to %s.", self.name, saved_availability)
        except Exception as exc:
            logger.error("[%s] Could not restore presence: %s", self.name, exc)

    # ------------------------------------------------------------------
    # Token management
    # ------------------------------------------------------------------

    def _get_token(self) -> str:
        """Return a valid access token, refreshing if needed."""
        if self._access_token and time.time() < self._token_expiry - 60:
            return self._access_token

        url = TOKEN_URL_TEMPLATE.format(tenant_id=self.tenant_id)
        resp = requests.post(
            url,
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "scope": "https://graph.microsoft.com/.default",
            },
            timeout=10,
        )
        resp.raise_for_status()
        token_data = resp.json()

        self._access_token = token_data["access_token"]
        self._token_expiry = time.time() + int(token_data.get("expires_in", 3600))
        return self._access_token
