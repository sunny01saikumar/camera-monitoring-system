#!/bin/bash
set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "=============================================="
echo "   RTSP Person Detection System Setup (Linux/Pi)"
echo "=============================================="

# Check system prerequisites
if ! command -v python3 &> /dev/null; then
    echo "Error: Python3 is not installed."
    exit 1
fi

# Ensure system dependencies for OpenCV and venv are present
echo "Ensuring required system libraries..."
if command -v apt-get &> /dev/null; then
    sudo apt-get update -y
    sudo apt-get install -y python3-venv python3-pip libgl1 libglib2.0-0
fi

# Create Virtual Environment
if [ ! -f "venv/bin/activate" ]; then
    echo "Creating clean Linux virtual environment..."
    rm -rf venv
    python3 -m venv venv
fi

# Activate Virtual Environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip and install packages
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install opencv-python-headless numpy Flask requests

# Download model
echo "Checking model weights..."
python3 download_model.py

# Launch application
echo "=============================================="
echo " Starting Person Detection Web Dashboard"
echo " Access URL: http://100.105.189.103:5000 or http://<your-pi-ip>:5000"
echo "=============================================="
python3 app.py
