#!/bin/bash

# HoloScope V0.2 Environment Setup Script
echo "🚀 Starting HoloScope Installation..."

# 1. Update System Packages
# sudo apt-get update && sudo apt-get upgrade -y

# 2. Install System Dependencies
echo "📦 Installing System Dependencies..."
sudo apt install -y python3-pip python3-venv nginx libcamera-dev gpiod

# 3. Create and Activate Virtual Environment
echo "📦 Setting up Python Virtual Environment..."
# Ensure we are in the correct directory
cd ~/HoloScopeV02
python3 -m venv venv --system-site-packages

source venv/bin/activate

# 4. Install Python Libraries
echo "🐍 Installing Python packages..."
pip install --upgrade pip
pip install fastapi uvicorn adafruit-blinka RPi.GPIO board
pip install adafruit-circuitpython-dht adafruit-circuitpython-bme280

# Handle local .whl for BME680
WHL_FILE="adafruit_circuitpython_bme680-3.7.13-py3-none-any.whl"
PACKAGE_NAME="adafruit-circuitpython-bme680"

if [ -f "$WHL_FILE" ]; then
    echo "📦 Installing local $PACKAGE_NAME..."
    pip install "$WHL_FILE"
else
    echo "⚠️  $WHL_FILE not found, attempting pip install..."
    pip install adafruit-circuitpython-bme680
fi

# 5. Enable Hardware Interfaces
echo "⚙️ Enabling Camera, I2C, and 1-Wire..."
sudo raspi-config nonint do_camera 0
sudo raspi-config nonint do_i2c 0
sudo raspi-config nonint do_onewire 0

# 6. AUTOMATION: Nginx Configuration
echo "🌐 Configuring Nginx..."
CONF_FILE="/etc/nginx/sites-available/holoscope"
sudo bash -c "cat > $CONF_FILE" <<EOF
server {
    listen 80;
    server_name _;
    root /home/pi/HoloScopeV02/web;
    index index.html;

    location / {
        try_files \$uri \$uri/ =404;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
    }

    location /stream/ {
        proxy_pass http://127.0.0.1:5000/stream/;
        proxy_buffering off;
    }
}
EOF

sudo ln -sf $CONF_FILE /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo chmod +x /home/pi
sudo chmod -R 755 /home/pi/HoloScopeV02
sudo systemctl restart nginx

# 8. Systemd Service (CREATED ONLY - NOT STARTED)
echo "🔄 Preparing HoloScope Systemd Service file..."
sudo bash -c "cat > /etc/systemd/system/holoscope.service" <<EOF
[Unit]
Description=HoloScope FastAPI Backend
After=network.target

[Service]
User=pi
WorkingDirectory=/home/pi/HoloScopeV02/app
ExecStart=/home/pi/HoloScopeV02/venv/bin/python main.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Reloading so the system sees the file, but NOT enabling/starting.
sudo systemctl daemon-reload

echo "✅ Installation Complete!"
echo "📡 Dashboard will be at: http://$(hostname -I | awk '{print $1}')"
echo "💡 The systemd service is prepared but NOT started."
echo "⚠️  Please run 'sudo reboot' now."
