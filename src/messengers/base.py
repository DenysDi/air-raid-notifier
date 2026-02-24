"""
Abstract base class for all messenger integrations.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class Status:
    """Represents a messenger user status snapshot."""
    text: str = ""
    emoji: str = ""
    extra: dict = field(default_factory=dict)  # platform-specific extras


class BaseMessenger(ABC):
    """
    All messenger integrations must implement this interface.
    The main loop will call:
      1. save_status()   – before the first alert
      2. set_alert()     – to activate the air-raid status
      3. restore_status()– when the alert ends
    """

    name: str = "base"

    def __init__(self, config: dict):
        self.config = config
        self._saved_status: Optional[Status] = None

    # ------------------------------------------------------------------
    # Core interface
    # ------------------------------------------------------------------

    @abstractmethod
    def get_status(self) -> Status:
        """Fetch the current status from the platform."""

    @abstractmethod
    def set_status(self, status: Status) -> None:
        """Push a status to the platform."""

    # ------------------------------------------------------------------
    # Helpers used by the main loop
    # ------------------------------------------------------------------

    def save_status(self) -> None:
        """Snapshot the current status so it can be restored later."""
        try:
            self._saved_status = self.get_status()
            logger.info("[%s] Saved current status: text=%r emoji=%r",
                        self.name, self._saved_status.text, self._saved_status.emoji)
        except Exception as exc:
            logger.error("[%s] Could not save status: %s", self.name, exc)
            self._saved_status = None

    def set_alert(self) -> None:
        """Switch to the air-raid status."""
        alert_status = Status(
            text=self.config.get("alert_text", "Air Raid 🚀"),
            emoji=self.config.get("alert_emoji", ":rotating_light:"),
        )
        try:
            self.set_status(alert_status)
            logger.info("[%s] Alert status set.", self.name)
        except Exception as exc:
            logger.error("[%s] Could not set alert status: %s", self.name, exc)

    def restore_status(self) -> None:
        """Restore the previously saved status."""
        if self._saved_status is None:
            logger.warning("[%s] No saved status to restore – skipping.", self.name)
            return
        try:
            self.set_status(self._saved_status)
            logger.info("[%s] Status restored.", self.name)
        except Exception as exc:
            logger.error("[%s] Could not restore status: %s", self.name, exc)
