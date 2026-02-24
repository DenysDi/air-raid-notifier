#!/usr/bin/env bash
# =============================================================================
#  install.sh – Air Raid Notifier installer for Ubuntu / Debian
#
#  Usage:
#    chmod +x install.sh
#    ./install.sh
#
#  What it does:
#    1. Verifies Python 3.9+ is available.
#    2. Creates a Python virtual environment in ./venv.
#    3. Installs pip dependencies.
#    4. Copies config.yaml.example → config.yaml (if not already present).
#    5. Installs a systemd user service so the notifier starts on login /
#       can be managed with systemctl --user.
# =============================================================================

set -euo pipefail

# ---- Colours ----------------------------------------------------------------
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()    { echo -e "${GREEN}[info]${NC}  $*"; }
warn()    { echo -e "${YELLOW}[warn]${NC}  $*"; }
error()   { echo -e "${RED}[error]${NC} $*"; exit 1; }

# ---- Resolve project root ---------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"

info "Project directory: $PROJECT_DIR"

# ---- Check Python -----------------------------------------------------------
PYTHON=""
for candidate in python3 python; do
    if command -v "$candidate" &>/dev/null; then
        version=$("$candidate" -c 'import sys; print(sys.version_info[:2])')
        if "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3,9) else 1)' 2>/dev/null; then
            PYTHON="$candidate"
            break
        fi
    fi
done

if [[ -z "$PYTHON" ]]; then
    error "Python 3.9 or newer is required. Install it with: sudo apt install python3"
fi
info "Using Python: $($PYTHON --version)"

# ---- Virtual environment ----------------------------------------------------
VENV_DIR="$PROJECT_DIR/venv"
if [[ ! -d "$VENV_DIR" ]]; then
    info "Creating virtual environment …"
    "$PYTHON" -m venv "$VENV_DIR"
else
    info "Virtual environment already exists – skipping creation."
fi

info "Installing dependencies …"
"$VENV_DIR/bin/pip" install --upgrade pip -q
"$VENV_DIR/bin/pip" install -r "$PROJECT_DIR/requirements.txt" -q
info "Dependencies installed."

# ---- Config -----------------------------------------------------------------
CONFIG_FILE="$PROJECT_DIR/config.yaml"
if [[ ! -f "$CONFIG_FILE" ]]; then
    cp "$PROJECT_DIR/config.yaml.example" "$CONFIG_FILE"
    warn "config.yaml created from example. Edit it before starting the service:"
    warn "  nano $CONFIG_FILE"
else
    info "config.yaml already exists – not overwriting."
fi

# ---- Systemd user service ---------------------------------------------------
SERVICE_NAME="air-raid-notifier"
SERVICE_DIR="$HOME/.config/systemd/user"
SERVICE_FILE="$SERVICE_DIR/${SERVICE_NAME}.service"

mkdir -p "$SERVICE_DIR"

cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=Air Raid Notifier
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=${PROJECT_DIR}
ExecStart=${VENV_DIR}/bin/python ${PROJECT_DIR}/src/main.py --config ${CONFIG_FILE}
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target
EOF

info "Systemd user service installed at: $SERVICE_FILE"

# Enable lingering so the service runs even when the user is not logged in.
if command -v loginctl &>/dev/null; then
    if loginctl show-user "$USER" 2>/dev/null | grep -q "Linger=no"; then
        info "Enabling lingering for user '$USER' (service runs without active login) …"
        sudo loginctl enable-linger "$USER" || warn "Could not enable linger – you may need to run: sudo loginctl enable-linger $USER"
    fi
fi

systemctl --user daemon-reload

echo ""
echo "======================================================"
echo "  Installation complete!"
echo "======================================================"
echo ""
echo "Next steps:"
echo ""
echo "  1. Edit your config:"
echo "       nano $CONFIG_FILE"
echo ""
echo "  2. Start the service:"
echo "       systemctl --user start $SERVICE_NAME"
echo ""
echo "  3. Enable auto-start on boot:"
echo "       systemctl --user enable $SERVICE_NAME"
echo ""
echo "  4. Check status / logs:"
echo "       systemctl --user status $SERVICE_NAME"
echo "       journalctl --user -u $SERVICE_NAME -f"
echo ""
echo "  5. Stop the service:"
echo "       systemctl --user stop $SERVICE_NAME"
echo ""
