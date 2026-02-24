#!/usr/bin/env python3
"""
Air Raid Notifier – main entry point.

Polls alerts.in.ua for the configured region and changes messenger
statuses when an air-raid alert starts/ends.

Usage:
    python src/main.py [--config path/to/config.yaml]
"""

import argparse
import logging
import signal
import sys
import time
from pathlib import Path

import requests
import yaml

from alerts import AlertsClient
from messengers import build_messengers

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s  %(levelname)-8s  %(name)s – %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def load_config(path: Path) -> dict:
    if not path.exists():
        sys.exit(f"Config file not found: {path}\n"
                 f"Copy config.yaml.example to config.yaml and fill in your values.")
    with path.open() as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------------------
# Graceful shutdown
# ---------------------------------------------------------------------------

_running = True


def _handle_signal(sig, frame):  # noqa: ANN001
    global _running
    logging.getLogger("main").info("Received signal %s – shutting down …", sig)
    _running = False


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def run(config: dict) -> None:
    log = logging.getLogger("main")

    alerts_cfg = config.get("alerts", {})
    poll_interval = int(alerts_cfg.get("poll_interval_seconds", 30))

    client = AlertsClient(alerts_cfg)
    messengers = build_messengers(config.get("messengers", {}))

    if not messengers:
        log.warning("No messengers are enabled – nothing to do. "
                    "Edit config.yaml and set at least one messenger to enabled: true.")

    alert_active = False

    log.info("Starting air-raid monitor for region UID %s (poll every %ds).",
             alerts_cfg.get("region_uid"), poll_interval)

    while _running:
        try:
            is_alert = client.check_alert()

            if is_alert and not alert_active:
                log.warning("🚨 ALERT STARTED – switching messenger statuses.")
                for m in messengers:
                    m.save_status()
                    m.set_alert()
                alert_active = True

            elif not is_alert and alert_active:
                log.info("✅ Alert ended – restoring messenger statuses.")
                for m in messengers:
                    m.restore_status()
                alert_active = False

        except requests.HTTPError as exc:
            log.error("HTTP error while checking alerts: %s", exc)
        except requests.RequestException as exc:
            log.error("Network error while checking alerts: %s", exc)
        except Exception as exc:
            log.exception("Unexpected error: %s", exc)

        # Sleep in small increments so we respond to signals quickly.
        deadline = time.monotonic() + poll_interval
        while _running and time.monotonic() < deadline:
            time.sleep(1)

    # On shutdown: restore statuses if an alert was active.
    if alert_active:
        log.info("Restoring statuses before exit …")
        for m in messengers:
            m.restore_status()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Air Raid Notifier")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(__file__).parent.parent / "config.yaml",
        help="Path to config.yaml (default: ../config.yaml relative to this script)",
    )
    args = parser.parse_args()

    config = load_config(args.config)
    setup_logging(config.get("log_level", "INFO"))

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    run(config)


if __name__ == "__main__":
    main()
