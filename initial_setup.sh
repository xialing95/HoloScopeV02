#!/bin/bash

# HoloScope V0.2 Environment Setup Script
echo "🚀 Starting HoloScope Installation..."

# 1. Update & Dependencies
echo "📦 Installing System Dependencies..."
sudo apt update && sudo apt install -y python3-pip python3-venv nginx libcamera-dev gpiod network-manager

# 2. Virtual Environment Setup
if [ ! -d "venv" ]; then
    echo "Creating new virtual environment..."
    python3 -m venv venv --system-site-packages
fi
source venv/bin/activate

# 3. Python Libraries
echo "🐍 Installing Python packages..."
pip install --upgrade pip
pip install fastapi uvicorn adafruit-blinka RPi.GPIO board \
            adafruit-circuitpython-dht adafruit-circuitpython-bme280

# Handle local .whl for BME680 if exists
WHL_FILE="adafruit_circuitpython_bme680-3.7.13-py3-none-any.whl"
if [ -f "$WHL_FILE" ]; then
    pip install "$WHL_FILE"
else
    pip install adafruit-circuitpython-bme680
fi

# 4. Hardware Interfaces
echo "⚙️ Enabling Hardware Interfaces..."
sudo raspi-config nonint do_camera 0
sudo raspi-config nonint do_i2c 0
sudo raspi-config nonint do_onewire 0

# 5. Nginx Configuration
echo "🌐 Configuring Nginx..."
CONF_FILE="/etc/nginx/sites-available/holoscope"
sudo bash -c "cat > $CONF_FILE" <<EOF
server {
    listen 80;
    server_name _;
    root $(pwd)/web;
    index index.html;
    client_max_body_size 100M;

    location / { try_files \$uri \$uri/ =404; }
    location /api/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_buffering off;
    }
}
EOF
sudo ln -sf $CONF_FILE /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo systemctl restart nginx

# 6. Network Permissions
echo "🔓 Configuring Network Permissions..."
echo "pi ALL=(ALL) NOPASSWD: /usr/bin/nmcli" | sudo tee /etc/sudoers.d/holoscope-nmcli

# 7. Create the Auto-Hotspot Script
echo "📡 Creating Auto-Hotspot Logic..."
cat > autohotspot.sh <<EOF
#!/bin/bash
# Wait for system to try connecting to known WiFi
sleep 15

if nmcli -t -f DEVICE,STATE dev | grep -q "wlan0:connected"; then
    echo "✅ Connected to WiFi."
else
    echo "❌ No WiFi. Starting HoloScope Hotspot..."
    SERIAL=\$(grep "Serial" /proc/cpuinfo | awk '{print \$3}' | tail -c 5)
    SSID="HoloScope-\${SERIAL:-XXXX}"
    
    sudo nmcli con delete "HoloscopeAP" > /dev/null 2>&1
    sudo nmcli con add type wifi ifname wlan0 mode ap con-name "HoloscopeAP" ssid "\$SSID" autoconnect false ipv4.method shared ipv4.addresses "192.168.4.1/24"
    sudo nmcli con modify "HoloscopeAP" 802-11-wireless.band bg 802-11-wireless-security.key-mgmt wpa-psk 802-11-wireless-security.psk "fishystuff"
    sudo nmcli con up "HoloscopeAP"
fi
EOF
chmod +x autohotspot.sh

# 8. Systemd Service Configuration
echo "🔄 Configuring Systemd Service..."
sudo bash -c "cat > /etc/systemd/system/holoscope.service" <<EOF
[Unit]
Description=HoloScope FastAPI Backend
After=network.target

[Service]
User=pi
WorkingDirectory=$(pwd)/app
# Run the hotspot check before starting the app
ExecStartPre=/bin/bash $(pwd)/autohotspot.sh
ExecStart=$(pwd)/venv/bin/python main.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable holoscope.service

echo "------------------------------------------------"
echo "✅ Installation Complete!"
echo "💡 At boot: If no WiFi is found, a hotspot named 'HoloScope-XXXX' will start."
echo "🔗 Hotspot Dashboard: http://192.168.4.1"
echo "⚠️  Please run 'sudo reboot' now."