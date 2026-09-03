#!/bin/bash
set -e

echo "=============================================="
echo "   Persistent Background Global Tunnel Setup"
echo "   Raspberry Pi 5 Auto-Boot Service"
echo "=============================================="

# Check if cloudflared is installed
if ! command -v cloudflared &> /dev/null; then
    echo "Installing Cloudflare Tunnel (cloudflared) for ARM64..."
    curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64.deb
    sudo dpkg -i cloudflared.deb
    rm cloudflared.deb
fi

echo "Installing systemd service /etc/systemd/system/global-tunnel.service..."

cat <<EOF | sudo tee /etc/systemd/system/global-tunnel.service > /dev/null
[Unit]
Description=Cloudflare Global Access Tunnel for Camera Monitoring
After=network.target network-online.target person-detection.service
Wants=network-online.target person-detection.service

[Service]
Type=simple
User=root
ExecStart=/usr/bin/cloudflared tunnel --url http://127.0.0.1:5000
Restart=always
RestartSec=5s
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

echo "Enabling and starting persistent background service..."
sudo systemctl daemon-reload
sudo systemctl enable global-tunnel
sudo systemctl restart global-tunnel

sleep 4

echo "=============================================="
echo "   PERSISTENT GLOBAL TUNNEL INSTALLED & ACTIVE!"
echo "   This tunnel runs 24/7 in the background."
echo "   You can close your SSH terminal anytime!"
echo "=============================================="
echo " Fetching your live HTTPS URL from systemd logs..."
echo "----------------------------------------------"
sudo journalctl -u global-tunnel -n 30 --no-pager | grep -i "trycloudflare.com" || true
echo "=============================================="
