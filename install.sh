#!/bin/bash

################################################################################
# SMS Daemon Service Installer
# This script installs the SMS daemon as a systemd service on Linux
################################################################################

set -e  # Exit on error

echo "============================================================"
echo "SMS Daemon Service Installer"
echo "============================================================"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "ERROR: This script must be run as root (use sudo)"
    echo "Usage: sudo bash install.sh"
    exit 1
fi

# Get the actual user (not root)
if [ -n "$SUDO_USER" ]; then
    ACTUAL_USER="$SUDO_USER"
    ACTUAL_HOME=$(getent passwd "$SUDO_USER" | cut -d: -f6)
else
    ACTUAL_USER="$USER"
    ACTUAL_HOME="$HOME"
fi

echo "Installing service for user: $ACTUAL_USER"
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
echo "SMS Daemon directory: $SCRIPT_DIR"
echo ""

# Check if required files exist
if [ ! -f "$SCRIPT_DIR/sms_sender.py" ]; then
    echo "ERROR: sms_sender.py not found in $SCRIPT_DIR"
    exit 1
fi

if [ ! -f "$SCRIPT_DIR/config.py" ]; then
    echo "ERROR: config.py not found!"
    echo "Please copy config.py.example to config.py and configure it first"
    exit 1
fi

# Find Python 3
SYSTEM_PYTHON=$(which python3)
if [ -z "$SYSTEM_PYTHON" ]; then
    echo "ERROR: Python 3 not found. Please install python3"
    exit 1
fi
echo "Python 3 found: $SYSTEM_PYTHON"

# Create virtual environment
VENV_DIR="$SCRIPT_DIR/venv"
echo ""
echo "Creating virtual environment..."
if [ -d "$VENV_DIR" ]; then
    echo "Virtual environment already exists, recreating..."
    rm -rf "$VENV_DIR"
fi

$SYSTEM_PYTHON -m venv "$VENV_DIR"
echo "Virtual environment created at: $VENV_DIR"

# Activate virtual environment and install dependencies
PYTHON_BIN="$VENV_DIR/bin/python"
PIP_BIN="$VENV_DIR/bin/pip"

echo ""
echo "Installing dependencies from requirements.txt..."
if [ -f "$SCRIPT_DIR/requirements.txt" ]; then
    $PIP_BIN install --upgrade pip
    $PIP_BIN install -r "$SCRIPT_DIR/requirements.txt"
    echo "Dependencies installed successfully"
else
    echo "WARNING: requirements.txt not found, installing basic dependencies..."
    $PIP_BIN install pyserial mysql-connector-python python-gsmmodem
fi

echo ""
echo "Verifying installation..."
$PYTHON_BIN -c "import serial; import mysql.connector; import gsmmodem; print('All dependencies OK')"
echo ""

# Create systemd service file
SERVICE_FILE="/etc/systemd/system/sms-daemon.service"
echo "Creating systemd service: $SERVICE_FILE"

cat > "$SERVICE_FILE" << EOF
[Unit]
Description=SMS Daemon Service
After=network.target mysql.service
Wants=mysql.service

[Service]
Type=simple
User=root
WorkingDirectory="$SCRIPT_DIR"
ExecStart="$VENV_DIR/bin/python" "$SCRIPT_DIR/sms_sender.py"
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Environment
Environment="PYTHONUNBUFFERED=1"

[Install]
WantedBy=multi-user.target
EOF

echo "Service file created"
echo ""

# Set proper permissions
echo "Setting permissions..."
chown -R root:root "$SCRIPT_DIR/venv"
chown root:root "$SCRIPT_DIR"/*.py
chmod +x "$SCRIPT_DIR/sms_sender.py"

# Reload systemd
echo "Reloading systemd daemon..."
systemctl daemon-reload

echo ""
echo "============================================================"
echo "Installation Complete!"
echo "============================================================"
echo ""
echo "Service Commands:"
echo "  Start service:    sudo systemctl start sms-daemon"
echo "  Stop service:     sudo systemctl stop sms-daemon"
echo "  Restart service:  sudo systemctl restart sms-daemon"
echo "  View status:      sudo systemctl status sms-daemon"
echo "  View logs:        sudo journalctl -u sms-daemon -f"
echo "  Enable on boot:   sudo systemctl enable sms-daemon"
echo "  Disable on boot:  sudo systemctl disable sms-daemon"
echo ""
echo "Next Steps:"
echo "  1. Configure config.py with your settings"
echo "  2. Test: sudo systemctl start sms-daemon"
echo "  3. Check status: sudo systemctl status sms-daemon"
echo "  4. View logs: sudo journalctl -u sms-daemon -f"
echo "  5. Enable auto-start: sudo systemctl enable sms-daemon"
echo ""
