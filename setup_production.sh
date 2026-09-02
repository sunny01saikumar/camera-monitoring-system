#!/bin/bash
set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "=============================================="
echo "   Production Setup - Raspberry Pi 5"
echo "=============================================="

# Install system prerequisites
echo "Installing system dependencies..."
sudo apt-get update -y
sudo apt-get install -y python3-venv python3-pip libgl1 libglib2.0-0 git

# Virtual Environment Setup
if [ ! -f "venv/bin/activate" ]; then
    echo "Creating clean Linux virtual environment..."
    rm -rf venv
    python3 -m venv venv
fi

source venv/bin/activate

echo "Installing production packages (Gunicorn, Flask, OpenCV)..."
pip install --upgrade pip
pip install gunicorn opencv-python-headless numpy Flask requests

# Download model
echo "Checking model weights..."
python3 download_model.py

# Install systemd service with dynamic path detection
echo "Installing systemd service /etc/systemd/system/person-detection.service..."
INSTALL_DIR=$(pwd)

cat <<EOF | sudo tee /etc/systemd/system/person-detection.service > /dev/null
[Unit]
Description=RTSP Person Detection & Camera Monitoring Dashboard
After=network.target network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=${INSTALL_DIR}
ExecStart=${INSTALL_DIR}/venv/bin/gunicorn --workers 1 --threads 4 --bind 0.0.0.0:5000 wsgi:app
Restart=always
RestartSec=5s
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

echo "Enabling and starting systemd service..."
sudo systemctl daemon-reload
sudo systemctl enable person-detection
sudo systemctl restart person-detection

echo "=============================================="
echo "   PRODUCTION SERVICE INSTALLED SUCCESSFULLY!"
echo "   Status: sudo systemctl status person-detection"
echo "   Logs:   sudo journalctl -u person-detection -f"
echo "   Access: http://100.105.189.103:5000 or http://<your-pi-ip>:5000"
echo "=============================================="
