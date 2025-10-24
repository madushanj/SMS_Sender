#!/bin/bash

################################################################################
# SMS Daemon Service Uninstaller (Linux)
################################################################################

set -e

echo "============================================================"
echo "SMS Daemon Service Uninstaller"
echo "============================================================"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "ERROR: This script must be run as root (use sudo)"
    echo "Usage: sudo bash uninstall.sh"
    exit 1
fi

SERVICE_FILE="/etc/systemd/system/sms-daemon.service"

# Check if service exists
if [ ! -f "$SERVICE_FILE" ]; then
    echo "Service not found. Nothing to uninstall."
    exit 0
fi

echo "Stopping service..."
systemctl stop sms-daemon 2>/dev/null || true

echo "Disabling service..."
systemctl disable sms-daemon 2>/dev/null || true

echo "Removing service file..."
rm -f $SERVICE_FILE

echo "Reloading systemd..."
systemctl daemon-reload
systemctl reset-failed

echo ""
echo "============================================================"
echo "Uninstallation Complete!"
echo "============================================================"
echo ""
echo "The SMS Daemon service has been removed."
echo "Your files in the installation directory are still intact."
echo ""
