#!/bin/bash

HOTSPOT_NAME="Hotspot"

# Get all active wifi connection names
ACTIVE_WIFI_CONNS=$(nmcli -t -f NAME,TYPE connection show --active | grep wifi | cut -d: -f1)

echo "Switching from WiFi (ACTIVE_WIFI_CONNS) to Hotspot ($HOTSPOT_NAME)..."


if [ -z "$ACTIVE_WIFI_CONNS" ]; then
    echo "No active WiFi connections found."
else
    for CON in $ACTIVE_WIFI_CONNS; do
        echo "Disconnecting WiFi connection: $CON"
        sudo nmcli connection down "$CON"
    done
fi

echo "All active WiFi client connections are turned off."

# Start the hotspot connection
echo "Starting hotspot $HOTSPOT_NAME..."
sudo nmcli connection up "$HOTSPOT_NAME"

# Display device status
nmcli device status

echo "Switch complete."
