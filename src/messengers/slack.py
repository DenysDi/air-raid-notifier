"""
Slack messenger integration.

Required setup:
  1. Go to https://api.slack.com/apps and create a new app (or use an existing one).
  2. Under "OAuth & Permissions" add the User Token Scope:
       - users.profile:read
       - users.profile:write
  3. Install the app to your workspace and copy the "User OAuth Token" (starts with xoxp-).
  4. Set that token in config.yaml under messengers.slack.token.

The integration saves/restores:
  - status_text  (the text users see below your name)
  - status_emoji (the emoji shown next to your name, e.g. ":house:")
  - status_expiration (0 = no expiry – we always restore without expiry)
"""

import logging
import requests

from .base import BaseMessenger, Status

logger = logging.getLogger(__name__)

SLACK_API = "https://slack.com/api"


class SlackMessenger(BaseMessenger):
    name = "Slack"

    def __init__(self, config: dict):
        super().__init__(config)
        token = config.get("token", "")
        if not token:
            raise ValueError("slack.token is required")
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {token}"})

    # ------------------------------------------------------------------
    # BaseMessenger interface
    # ------------------------------------------------------------------

    def get_status(self) -> Status:
        resp = self.session.get(f"{SLACK_API}/users.profile.get", timeout=10)
        resp.raise_for_status()
        data = resp.json()
        self._check_slack_error(data, "users.profile.get")

        profile = data.get("profile", {})
        return Status(
            text=profile.get("status_text", ""),
            emoji=profile.get("status_emoji", ""),
        )

    def set_status(self, status: Status) -> None:
        payload = {
            "profile": {
                "status_text": status.text,
                "status_emoji": status.emoji,
                "status_expiration": 0,
            }
        }
        resp = self.session.post(
            f"{SLACK_API}/users.profile.set",
            json=payload,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        self._check_slack_error(data, "users.profile.set")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _check_slack_error(data: dict, endpoint: str) -> None:
        if not data.get("ok"):
            error = data.get("error", "unknown error")
            raise RuntimeError(f"Slack {endpoint} returned error: {error}")
