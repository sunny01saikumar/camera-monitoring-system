#!/bin/bash
set -e

echo "=============================================="
echo "   Global HTTPS Tunnel Setup for Raspberry Pi 5"
echo "   Access Dashboard from ANY Location Worldwide"
echo "=============================================="

# Check if cloudflared is installed
if ! command -v cloudflared &> /dev/null; then
    echo "Installing Cloudflare Tunnel (cloudflared) for ARM64..."
    curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64.deb
    sudo dpkg -i cloudflared.deb
    rm cloudflared.deb
fi

echo "Ensuring web server service is active..."
sudo systemctl restart person-detection || true
sleep 2

echo "=============================================="
echo " Starting Free Public HTTPS Global Tunnel..."
echo "=============================================="
echo "NOTE: Look for the 'https://...trycloudflare.com' link in the output below."
echo "Each time this command is run, Cloudflare generates a fresh live URL!"
echo "=============================================="

cloudflared tunnel --url http://127.0.0.1:5000


