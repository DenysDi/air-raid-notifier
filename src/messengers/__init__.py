"""
Messenger registry.
Add new integrations here – the main loop discovers them automatically.
"""

from typing import List

from .base import BaseMessenger
from .slack import SlackMessenger
from .teams import TeamsMessenger

_REGISTRY = {
    "slack": SlackMessenger,
    "teams": TeamsMessenger,
}


def build_messengers(messengers_config: dict) -> List[BaseMessenger]:
    """
    Instantiate and return all enabled messengers from the config block.

    Example config shape:
        messengers:
          slack:
            enabled: true
            token: "xoxp-..."
          teams:
            enabled: false
    """
    active: List[BaseMessenger] = []
    for name, cls in _REGISTRY.items():
        cfg = messengers_config.get(name, {})
        if not cfg.get("enabled", False):
            continue
        try:
            instance = cls(cfg)
            active.append(instance)
        except Exception as exc:
            import logging
            logging.getLogger(__name__).error(
                "Failed to initialise %s messenger: %s", name, exc
            )
    return active
