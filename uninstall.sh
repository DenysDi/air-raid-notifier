#!/usr/bin/env bash
# =============================================================================
#  uninstall.sh – removes the systemd service installed by install.sh
#  Does NOT delete config.yaml or the venv.
# =============================================================================

set -euo pipefail

SERVICE_NAME="air-raid-notifier"
SERVICE_FILE="$HOME/.config/systemd/user/${SERVICE_NAME}.service"

systemctl --user stop  "$SERVICE_NAME" 2>/dev/null || true
systemctl --user disable "$SERVICE_NAME" 2>/dev/null || true

if [[ -f "$SERVICE_FILE" ]]; then
    rm -f "$SERVICE_FILE"
    systemctl --user daemon-reload
    echo "Service removed: $SERVICE_FILE"
else
    echo "Service file not found – nothing to remove."
fi

echo "Done. The config.yaml and venv directory were not removed."
