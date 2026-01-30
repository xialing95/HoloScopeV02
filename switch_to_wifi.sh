#!/bin/bash

# Check if SSID and PASSWORD are provided as arguments
if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <WiFi_SSID> <WiFi_Password>"
    exit 1
fi

HOTSPOT_NAME="Hotspot"
WIFI_SSID="$1"
WIFI_PASSWORD="$2"
WLAN_INTERFACE="wlan0"

echo "Switching from Hotspot ($HOTSPOT_NAME) to WiFi client ($WIFI_SSID)..."

# Bring down the hotspot
sudo nmcli connection down "$HOTSPOT_NAME"

# Try to connect to WiFi
if nmcli connection show | grep -q "$WIFI_SSID"; then
    echo "WiFi connection profile found. Bringing it up..."
    sudo nmcli connection up "$WIFI_SSID"
else
    echo "Creating WiFi connection profile and connecting..."
    sudo nmcli device wifi connect "$WIFI_SSID" password "$WIFI_PASSWORD" ifname "$WLAN_INTERFACE"
fi

# Wait a moment for connection to establish
sleep 30

# Check WiFi connection status
CON_STATUS=$(nmcli -t -f DEVICE,STATE device status | grep '^wlan0:' | cut -d: -f2)

if [ "$CON_STATUS" = "connected" ]; then
    echo "WiFi connected successfully."
else
    echo "WiFi connection failed! Re-enabling hotspot..."

    # Bring WiFi down to prevent conflicts
    sudo nmcli connection down "$WIFI_SSID"

    # Bring hotspot back up
    sudo nmcli connection up "$HOTSPOT_NAME"

    if [ $? -eq 0 ]; then
        echo "Hotspot re-enabled successfully."
    else
        echo "Failed to re-enable hotspot. Please check manually."
    fi
fi

# Show current wifi device status
nmcli device status

echo "Script complete."
