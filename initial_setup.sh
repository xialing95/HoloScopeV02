#!/bin/bash

# HoloScope V0.2.1 - Enhanced Setup
echo "Starting HoloScope Installation..."

# Define Absolute Path
INSTALL_DIR="/home/pi/HoloScope"
mkdir -p $INSTALL_DIR

# 1. Update & Dependencies
echo "Installing System Dependencies..."
sudo apt update && sudo apt install -y \
python3-pip python3-venv nginx libcamera-dev \
gpiod network-manager python3-pil libjpeg-dev zlib1g-dev

# 2. Virtual Environment Setup
if [ ! -d "$INSTALL_DIR/venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv $INSTALL_DIR/venv --system-site-packages
fi
source $INSTALL_DIR/venv/bin/activate

# 3. Python Libraries
pip install --upgrade pip
pip install fastapi uvicorn adafruit-blinka RPi.GPIO board \
            adafruit-circuitpython-dht adafruit-circuitpython-bme280 \
            adafruit-circuitpython-bme680

# 4. Hardware Interfaces
sudo raspi-config nonint do_camera 0
sudo raspi-config nonint do_i2c 0

# 5. Optimized Nginx Configuration
echo "🌐 Configuring Nginx..."
CONF_FILE="/etc/nginx/sites-available/holoscope"
sudo bash -c "cat > $CONF_FILE" <<EOF
server {
    listen 80;
    server_name _;
    root $INSTALL_DIR/web;
    index index.html;

    location / {
        try_files \$uri \$uri/ =404;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }
}
EOF
sudo ln -sf $CONF_FILE /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo systemctl restart nginx

# 6. Improved Auto-Hotspot Script
cat > $INSTALL_DIR/autohotspot.sh <<EOF
#!/bin/bash
# Check for WiFi 3 times before giving up
for i in {1..3}; do
    if nmcli -t -f DEVICE,STATE dev | grep -q "wlan0:connected"; then
        echo "WiFi Connected."
        exit 0
    fi
    sleep 5
done

echo "Starting Hotspot..."
SERIAL=\$(grep "Serial" /proc/cpuinfo | awk '{print \$3}' | tail -c 5)
SSID="HoloScope-\${SERIAL:-XXXX}"
sudo nmcli con delete "HoloscopeAP" > /dev/null 2>&1
sudo nmcli con add type wifi ifname wlan0 mode ap con-name "HoloscopeAP" ssid "\$SSID" autoconnect false ipv4.method shared ipv4.addresses "192.168.4.1/24"
sudo nmcli con modify "HoloscopeAP" 802-11-wireless.band bg 802-11-wireless-security.key-mgmt wpa-psk 802-11-wireless-security.psk "fishystuff"
sudo nmcli con up "HoloscopeAP"
EOF
chmod +x $INSTALL_DIR/autohotspot.sh

# 7. Standardized Systemd Service
sudo bash -c "cat > /etc/systemd/system/holoscope.service" <<EOF
[Unit]
Description=HoloScope FastAPI Backend
After=network.target

[Service]
User=pi
WorkingDirectory=$INSTALL_DIR/app
ExecStartPre=/bin/bash $INSTALL_DIR/autohotspot.sh
# Explicitly calling uvicorn from venv on port 8000
ExecStart=$INSTALL_DIR/venv/bin/python3 -m uvicorn main:app --host 127.0.0.1 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable holoscope.service
sudo chmod +x /home/pi
echo "Setup Complete. Run 'sudo reboot' to apply."